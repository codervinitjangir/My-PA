"""Microphone capture for push-to-talk, in the format Whisper expects.

Two capture strategies, selected by ``always_on``:

``always_on=True`` (default)
    The input stream stays open for the process lifetime, continuously filling
    a short circular buffer that overwrites itself. Pressing the hotkey does
    not *start* the microphone -- it marks where in an already-flowing stream
    to begin keeping audio, and prepends the pre-roll. Opening an audio device
    on Windows costs 100-300 ms, which is long enough to swallow the first
    syllable of a sentence; this avoids that entirely.

``always_on=False``
    The device is opened when the hotkey goes down and closed when it comes up,
    so nothing is capturable while Bruno is idle. Stricter, at the cost of the
    device startup delay described above.

In neither mode is audio written to disk or transmitted by this module. The
pre-roll buffer is bounded, lives in memory, and is continuously discarded.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import numpy as np
import sounddevice as sd

from voice.audio.devices import DeviceInfo, resolve_device

logger = logging.getLogger(__name__)

# Whisper operates on 16 kHz mono float32. Recording natively in that format
# avoids a resampling pass that would cost both latency and fidelity.
SAMPLE_RATE: Final = 16_000
CHANNELS: Final = 1
DTYPE: Final = "float32"

BLOCK_MS: Final = 30
BLOCK_FRAMES: Final = SAMPLE_RATE * BLOCK_MS // 1000

DEFAULT_PREROLL_MS: Final = 300
DEFAULT_MIN_DURATION_MS: Final = 200

# A held key, a stuck key, or hands-free mode in a noisy room can otherwise
# record without limit. Whisper also processes long audio in 30-second windows,
# so a five-minute clip costs minutes of transcription for a request nobody is
# still waiting on.
DEFAULT_MAX_DURATION_MS: Final = 60_000


@dataclass(frozen=True, slots=True)
class AudioClip:
    """A finished recording, ready for transcription."""

    samples: np.ndarray
    sample_rate: int = SAMPLE_RATE

    @property
    def duration(self) -> float:
        """Length in seconds."""
        return len(self.samples) / self.sample_rate

    @property
    def peak(self) -> float:
        """Loudest absolute sample, in 0.0-1.0. Near zero means a silent mic."""
        return float(np.max(np.abs(self.samples))) if self.samples.size else 0.0

    @property
    def is_silent(self) -> bool:
        """Whether the clip is quiet enough to be a muted or wrong device."""
        return self.peak < 0.01


class RecorderError(RuntimeError):
    """The microphone could not be opened or read."""


class AudioRecorder:
    """Records microphone audio for the duration of a hotkey press.

    Not reentrant: one capture at a time. ``begin_capture`` while already
    capturing is ignored rather than raising, because the caller is a hotkey
    handler and a duplicated key event should not crash the application.

    Args:
        device_name: Substring of the microphone name, or ``None`` for the
            system default.
        always_on: Keep the stream open between captures. See module docstring.
        preroll_ms: Audio retained from *before* the key press. Only meaningful
            when ``always_on`` is set.
        min_duration_ms: Captures shorter than this are discarded as accidental
            taps, so a stray keypress cannot trigger a transcription.
        max_duration_ms: Audio beyond this is dropped. A stuck key or a noisy
            room in hands-free mode would otherwise record without limit.
    """

    def __init__(
        self,
        *,
        device_name: str | None = None,
        always_on: bool = True,
        preroll_ms: int = DEFAULT_PREROLL_MS,
        min_duration_ms: int = DEFAULT_MIN_DURATION_MS,
        max_duration_ms: int = DEFAULT_MAX_DURATION_MS,
    ) -> None:
        self._device_name = device_name
        self._always_on = always_on
        self._min_duration = min_duration_ms / 1000
        self._max_samples = int(SAMPLE_RATE * max_duration_ms / 1000)
        self._preroll_blocks = max(1, preroll_ms // BLOCK_MS) if always_on else 0

        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._device: DeviceInfo | None = None
        self._capturing = False
        self._captured: list[np.ndarray] = []
        self._preroll: deque[np.ndarray] = deque(maxlen=self._preroll_blocks or 1)
        self._preroll_samples = 0
        self._captured_samples = 0
        self._hit_limit = False
        self._overflows = 0
        self._listeners: list[Callable[[np.ndarray], None]] = []

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Prepare the recorder, opening the device if running always-on."""
        if self._always_on:
            self._open_stream()
            logger.info(
                "Microphone open on %s (pre-roll %d ms)",
                self._device,
                self._preroll_blocks * BLOCK_MS,
            )
        else:
            # Resolve now so a bad device name fails at startup rather than
            # on the user's first press.
            self._device = resolve_device(self._device_name, "input")
            logger.info("Microphone %s will open on demand", self._device)

    def stop(self) -> None:
        """Close the device and drop any buffered audio."""
        self._close_stream()
        with self._lock:
            self._capturing = False
            self._captured.clear()
            self._preroll.clear()

    def __enter__(self) -> AudioRecorder:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()

    @property
    def device(self) -> DeviceInfo | None:
        """The resolved input device, once ``start`` has run."""
        return self._device

    def subscribe(self, listener: Callable[[np.ndarray], None]) -> None:
        """Receive every captured block, whether or not a capture is active.

        Used by hands-free mode to watch for speech continuously. Listeners
        run on the realtime audio thread, so they must do nothing but hand the
        block off -- typically onto a queue. Blocking here causes dropouts.
        """
        self._listeners.append(listener)

    # -- capture ------------------------------------------------------------

    def begin_capture(self, *, use_preroll: bool = True) -> None:
        """Start keeping audio. Safe to call from a hotkey handler.

        Args:
            use_preroll: Include the moment before the key was pressed. Set
                False when interrupting Bruno mid-sentence: on speakers the
                pre-roll holds Bruno's own voice, which would otherwise be
                transcribed as if the user had said it.
        """
        with self._lock:
            if self._capturing:
                logger.debug("begin_capture ignored; already capturing")
                return
            # Seeding with the pre-roll is what recovers the moment before the
            # key was pressed. Empty when always_on is disabled.
            self._captured = list(self._preroll) if use_preroll else []
            # Remembered so the tap guard can measure only the audio the user
            # actually held for. Counting the pre-roll would let a 90 ms brush
            # of the key clear a 200 ms threshold.
            self._preroll_samples = sum(len(block) for block in self._captured)
            self._captured_samples = self._preroll_samples
            self._hit_limit = False
            self._preroll.clear()
            self._capturing = True

        if not self._always_on:
            self._open_stream()

    def end_capture(self) -> AudioClip | None:
        """Stop keeping audio and return what was recorded.

        Returns:
            The clip, or ``None`` if nothing was being captured or the press
            was too brief to be intentional.
        """
        with self._lock:
            if not self._capturing:
                return None
            self._capturing = False
            blocks = self._captured
            preroll_samples = self._preroll_samples
            self._captured = []
            self._preroll_samples = 0
            self._captured_samples = 0

        if not self._always_on:
            self._close_stream()

        if not blocks:
            logger.debug("Capture produced no audio")
            return None

        samples = np.concatenate(blocks)
        held_duration = (len(samples) - preroll_samples) / SAMPLE_RATE
        if held_duration < self._min_duration:
            logger.debug("Discarding %.0f ms tap", held_duration * 1000)
            return None

        clip = AudioClip(samples)

        if self._overflows:
            logger.warning(
                "Dropped %d input block(s) during capture; audio may be choppy",
                self._overflows,
            )
            self._overflows = 0

        return clip

    # -- stream plumbing ----------------------------------------------------

    def _open_stream(self) -> None:
        if self._stream is not None:
            return

        self._device = resolve_device(self._device_name, "input")
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_FRAMES,
                device=self._device.index,
                callback=self._on_audio,
            )
            stream.start()
        except sd.PortAudioError as exc:
            raise RecorderError(f"Could not open microphone {self._device}: {exc}") from exc

        self._stream = stream

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except sd.PortAudioError:
            logger.exception("Error closing microphone stream")

    def _on_audio(
        self,
        indata: np.ndarray,
        _frames: int,
        _time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """PortAudio callback. Runs on a realtime thread -- keep it cheap.

        Blocking here starves the audio device and produces dropouts, so this
        does nothing but copy the block into a buffer. ``indata`` is reused by
        PortAudio between calls and must be copied, not referenced.
        """
        if status:
            self._overflows += 1

        block = indata[:, 0].copy()
        with self._lock:
            if self._capturing:
                if self._captured_samples < self._max_samples:
                    self._captured.append(block)
                    self._captured_samples += len(block)
                elif not self._hit_limit:
                    self._hit_limit = True
                    logger.warning(
                        "Recording hit the %.0fs limit; ignoring the rest",
                        self._max_samples / SAMPLE_RATE,
                    )
            elif self._preroll_blocks:
                self._preroll.append(block)

        for listener in self._listeners:
            try:
                listener(block)
            except Exception:  # noqa: BLE001 -- a bad listener must not stop capture
                logger.exception("Audio listener raised")
