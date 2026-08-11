"""Streaming audio playback.

Audio is written as it is produced rather than assembled and then played. A
callback-driven output stream pulls from a byte buffer that the synthesiser
fills concurrently, so sound starts as soon as the first fragment exists and
the rest arrives while earlier audio is still playing.

The alternative -- synthesise fully, then play -- would add the entire
synthesis time to the silence before Bruno makes a sound, and that silence would
grow with the length of the reply.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Final

import sounddevice as sd

from voice.audio.devices import DeviceInfo, resolve_device

logger = logging.getLogger(__name__)

BYTES_PER_SAMPLE: Final = 2  # 16-bit PCM
DRAIN_POLL_SECONDS: Final = 0.01

# Stops a genuinely broken device from being reopened on every written chunk,
# which would spend more time failing than playing.
RECOVERY_COOLDOWN_SECONDS: Final = 2.0


class PlaybackError(RuntimeError):
    """The output device could not be opened."""


class StreamingPlayer:
    """Plays 16-bit mono PCM as it is written.

    Args:
        sample_rate: Rate of the audio that will be written.
        device_name: Substring of the output device name, or ``None`` for the
            system default.
        latency: PortAudio latency hint. ``'low'`` keeps the buffer small so
            playback starts promptly, at a slightly higher risk of underruns.
    """

    def __init__(
        self,
        sample_rate: int,
        *,
        device_name: str | None = None,
        latency: str | float = "low",
    ) -> None:
        self._sample_rate = sample_rate
        self._device_name = device_name
        self._latency = latency

        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stream: sd.RawOutputStream | None = None
        self._device: DeviceInfo | None = None
        self._underruns = 0
        self._last_recovery = 0.0

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Open the output device. Idempotent."""
        if self._stream is not None:
            return

        self._device = resolve_device(self._device_name, "output")
        try:
            stream = sd.RawOutputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                device=self._device.index,
                latency=self._latency,
                callback=self._on_request,
            )
            stream.start()
        except sd.PortAudioError as exc:
            raise PlaybackError(f"Could not open speaker {self._device}: {exc}") from exc

        self._stream = stream
        logger.info("Playback open on %s at %d Hz", self._device, self._sample_rate)

    def stop(self) -> None:
        """Close the device and discard anything unplayed."""
        self.flush()
        self._close_stream()

    def __enter__(self) -> StreamingPlayer:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()

    @property
    def device(self) -> DeviceInfo | None:
        """The resolved output device, once started."""
        return self._device

    # -- writing ------------------------------------------------------------

    def write(self, pcm: bytes) -> None:
        """Queue raw PCM for playback. Returns immediately."""
        if not pcm:
            return
        self._ensure_stream()
        with self._lock:
            self._buffer.extend(pcm)

    def _ensure_stream(self) -> None:
        """Reopen playback if the device went away.

        Unplugging headphones mid-sentence stops the stream, and PortAudio
        reports this by simply going inactive rather than raising. Without
        recovery Bruno stays mute until it is restarted, which reads as a crash.
        Reopening resolves the device by name again, so audio follows the user
        to whatever is now the default.
        """
        stream = self._stream
        if stream is not None and stream.active:
            return

        now = time.perf_counter()
        if now - self._last_recovery < RECOVERY_COOLDOWN_SECONDS:
            return
        self._last_recovery = now

        logger.warning("Playback device stopped responding; reopening")
        self._close_stream()
        try:
            self.start()
        except (PlaybackError, Exception):  # noqa: BLE001 -- keep Bruno alive
            logger.exception("Could not reopen the playback device")

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:  # noqa: BLE001 -- the device may already be gone
            logger.debug("Error closing the old playback stream", exc_info=True)

    @property
    def pending_seconds(self) -> float:
        """Seconds of audio queued but not yet played."""
        with self._lock:
            queued = len(self._buffer)
        return queued / (self._sample_rate * BYTES_PER_SAMPLE)

    def wait_until_drained(self, timeout: float | None = None) -> bool:
        """Block until everything written has been played.

        Args:
            timeout: Seconds to wait, or ``None`` to wait indefinitely.

        Returns:
            True if the buffer emptied, False if the timeout expired.
        """
        deadline = None if timeout is None else time.perf_counter() + timeout
        while self.pending_seconds > 0:
            stream = self._stream
            if stream is None or not stream.active:
                # The device died with audio still queued. Waiting for a
                # buffer nothing is consuming would hang until the timeout,
                # freezing Bruno for as long as it allows.
                logger.warning("Playback stopped with audio still queued")
                self.flush()
                return False
            if deadline is not None and time.perf_counter() >= deadline:
                return False
            time.sleep(DRAIN_POLL_SECONDS)
        return True

    def flush(self) -> None:
        """Drop unplayed audio, stopping playback almost immediately.

        Used to interrupt Bruno mid-sentence. Only audio already handed to the
        sound card continues, which is a few milliseconds at this buffer size.
        """
        with self._lock:
            self._buffer.clear()

    # -- realtime callback --------------------------------------------------

    def _on_request(
        self,
        outdata: memoryview,
        frames: int,
        _time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """PortAudio callback. Runs on a realtime thread -- keep it cheap.

        Any blocking work here causes audible dropouts, so this only copies
        bytes. A short buffer is padded with silence rather than raising:
        during streaming it is normal for synthesis to be momentarily behind.
        """
        if status.output_underflow:
            self._underruns += 1

        needed = frames * BYTES_PER_SAMPLE
        with self._lock:
            available = min(needed, len(self._buffer))
            chunk = bytes(self._buffer[:available])
            del self._buffer[:available]

        if available < needed:
            chunk += b"\x00" * (needed - available)
        outdata[:] = chunk
