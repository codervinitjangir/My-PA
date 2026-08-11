"""Speech synthesis with Piper.

Piper is used as a long-lived subprocess rather than through its Python
bindings. The bindings require a system-wide espeak-ng installation, which
would put a manual step between a user and a working install; the released
binary carries its own dependencies and drops straight into an installer.

Two measurements shaped this design. Launching Piper per utterance costs
roughly 1.5 s, almost all of it loading a 60 MB model. Keeping one process
alive and feeding it a sentence at a time gives first audio in about 215 ms.
Piper also synthesises per *line* of input, so a whole paragraph written at
once produces nothing until all of it is finished -- feeding sentences is what
makes the stream actually stream.

    launch once ──► warm up ──► sentence ──► audio ──► sentence ──► audio
      ~1.0 s        hidden       215 ms              215 ms
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Final

from voice.audio.devices import DeviceInfo
from voice.audio.player import StreamingPlayer
from core import paths
from voice.tts.chunker import split_stream

logger = logging.getLogger(__name__)

# Chosen by ear against four alternatives. A companion's voice is the most
# noticeable thing about it, and this is the one that sounds like someone
# rather than something.
DEFAULT_VOICE: Final = "en_US-norman-medium"

READ_CHUNK_BYTES: Final = 2048

# Piper emits no end-of-utterance marker on a shared stdout stream, so the end
# of a reply is inferred from a gap in output. It synthesises at 5-6x realtime,
# so a pause this long means it has genuinely stopped rather than fallen behind.
IDLE_GAP_SECONDS: Final = 0.4

# Synthesis takes 215-290 ms to produce its first bytes. Waiting only for a gap
# in output would see the silence *before* synthesis begins and conclude that
# Bruno had finished, cutting it off before its first word.
FIRST_AUDIO_TIMEOUT_SECONDS: Final = 15.0
SPEAK_TIMEOUT_SECONDS: Final = 120.0

WARMUP_TEXT: Final = "Ready."


class TTSError(RuntimeError):
    """Speech synthesis is unavailable or failed."""


class PiperVoice:
    """Streams synthesised speech from a persistent Piper process.

    Satisfies :class:`~bruno.core.protocols.TTSEngine`.

    Not safe for concurrent calls: one utterance at a time, which matches a
    companion that speaks when spoken to.

    Args:
        voice: Voice name, matching ``<name>.onnx`` in ``voice_dir``.
        voice_dir: Directory holding downloaded voices. ``None`` resolves at
            construction, which differs between a checkout and a packaged run.
        binary: Path to ``piper.exe``. ``None`` resolves to the copy shipped
            inside the bundle.
        output_device: Substring of the speaker name, or ``None`` for default.
        speed: Length scale. Values above 1.0 slow speech down; Piper's own
            default of 1.0 is already close to natural pace.
    """

    def __init__(
        self,
        *,
        voice: str = DEFAULT_VOICE,
        voice_dir: Path | None = None,
        binary: Path | None = None,
        output_device: str | None = None,
        speed: float = 1.0,
    ) -> None:
        voice_dir = voice_dir or paths.voices_dir()
        self._voice = voice
        self._model = voice_dir / f"{voice}.onnx"
        self._config = voice_dir / f"{voice}.onnx.json"
        self._binary = binary or paths.piper_binary()
        self._speed = speed

        self._sample_rate = self._read_sample_rate()
        self._player = StreamingPlayer(self._sample_rate, device_name=output_device)

        self._process: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._last_output = 0.0
        self._audio_bytes = 0
        self._output_lock = threading.Lock()
        self._speaking = threading.Event()
        self._interrupted = threading.Event()
        # Counts audio but never plays it. Distinct from _interrupted, which
        # also aborts the wait it is used in.
        self._discard = threading.Event()

    # -- setup --------------------------------------------------------------

    def _read_sample_rate(self) -> int:
        """Read the voice's sample rate from its config.

        Voices differ, and playing 22.05 kHz audio at 16 kHz produces a slow,
        deep voice rather than an error, so this is read rather than assumed.
        """
        if not self._config.is_file():
            raise TTSError(
                f"Voice config not found: {self._config}\n"
                f"Run: python -m scripts.setup --voice {self._voice}"
            )
        try:
            data = json.loads(self._config.read_text(encoding="utf-8"))
            return int(data["audio"]["sample_rate"])
        except (OSError, ValueError, KeyError) as exc:
            raise TTSError(f"Could not read sample rate from {self._config}: {exc}") from exc

    @property
    def name(self) -> str:
        """Voice identifier, for logs."""
        return f"piper/{self._voice}"

    @property
    def sample_rate(self) -> int:
        """Rate of the audio this voice produces."""
        return self._sample_rate

    @property
    def output_device(self) -> DeviceInfo | None:
        """The speaker in use, once started."""
        return self._player.device

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Launch Piper, open the speaker, and warm the model up.

        Raises:
            TTSError: If the binary or voice is missing, or Piper will not run.
        """
        if self._process is not None:
            return

        if not self._binary.is_file():
            raise TTSError(
                f"Piper not found at {self._binary}\nRun: python -m scripts.setup"
            )
        if not self._model.is_file():
            raise TTSError(
                f"Voice not found: {self._model}\n"
                f"Run: python -m scripts.setup --voice {self._voice}"
            )

        self._player.start()

        try:
            self._process = subprocess.Popen(
                [
                    str(self._binary),
                    "--model", str(self._model),
                    "--length_scale", str(self._speed),
                    "--output_raw",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                # Piper resolves espeak-ng-data relative to its own directory.
                cwd=str(self._binary.parent),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            self._player.stop()
            raise TTSError(f"Could not start Piper: {exc}") from exc

        self._reader = threading.Thread(target=self._drain_stdout, name="ev-tts-read", daemon=True)
        self._reader.start()

        self._warm_up()
        logger.info("%s ready at %d Hz", self.name, self._sample_rate)

    def _warm_up(self) -> None:
        """Absorb the model-load cost before anyone is waiting on it.

        Measured at roughly 970 ms for the first sentence against 215 ms
        afterwards. Output is discarded so nothing is heard.
        """
        started = time.perf_counter()
        with self._output_lock:
            self._audio_bytes = 0

        # Discard at the reader rather than flushing afterwards: audio queued
        # even briefly can reach the sound card, and a clipped syllable on
        # every launch is worse than no warm-up at all.
        self._discard.set()
        try:
            self._write_line(WARMUP_TEXT)
            self._await_first_audio()
        finally:
            self._discard.clear()
            self._player.flush()
        logger.debug("Voice warm-up took %.0f ms", (time.perf_counter() - started) * 1000)

    def stop(self) -> None:
        """Terminate Piper and close the speaker."""
        self._interrupted.set()
        process, self._process = self._process, None

        if process is not None:
            try:
                if process.stdin:
                    process.stdin.close()
                process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()

        if self._reader is not None:
            self._reader.join(timeout=2.0)
            self._reader = None

        self._player.stop()
        logger.info("%s stopped", self.name)

    def __enter__(self) -> PiperVoice:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()

    # -- speaking -----------------------------------------------------------

    def speak(self, text: str) -> None:
        """Speak a complete string, blocking until playback finishes."""
        self.speak_stream([text])

    def speak_stream(self, fragments: Iterable[str]) -> None:
        """Speak text arriving as a stream, blocking until playback finishes.

        Sentences are synthesised as they complete, so Bruno begins speaking while
        later text is still being generated.

        Args:
            fragments: Text chunks in order, such as an LLM token stream.

        Raises:
            TTSError: If Piper is not running or has exited.
        """
        for _ in self.stream_sentences(fragments):
            pass
        self._await_idle()
        self._player.wait_until_drained(timeout=SPEAK_TIMEOUT_SECONDS)

    def stream_sentences(self, fragments: Iterable[str]) -> Iterator[str]:
        """Speak a fragment stream, yielding each sentence as it is sent.

        Yields rather than returning so callers can display what is being said
        without waiting for the whole reply.

        Args:
            fragments: Text chunks in order.

        Yields:
            Each sentence handed to the synthesiser.
        """
        self._interrupted.clear()
        self._speaking.set()
        with self._output_lock:
            self._audio_bytes = 0
        try:
            for sentence in split_stream(fragments):
                if self._interrupted.is_set():
                    return
                self._write_line(sentence)
                yield sentence
        finally:
            self._speaking.clear()

    def wait_until_spoken(self, timeout: float = SPEAK_TIMEOUT_SECONDS) -> bool:
        """Block until synthesis has finished and playback has drained.

        Callers that drive :meth:`stream_sentences` themselves need this, since
        that method returns once the last sentence is *queued*, not spoken.

        Returns:
            True if speech completed, False on timeout.
        """
        finished = self._await_idle(timeout)
        drained = self._player.wait_until_drained(timeout=timeout)
        return finished and drained

    def interrupt(self) -> None:
        """Stop speaking as soon as possible.

        Audio already queued is discarded. Anything Piper is mid-way through
        synthesising still arrives and is dropped by the reader thread.
        """
        self._interrupted.set()
        self._player.flush()

    @property
    def is_speaking(self) -> bool:
        """Whether audio is being produced or is still queued."""
        return self._speaking.is_set() or self._player.pending_seconds > 0

    # -- process plumbing ---------------------------------------------------

    def _write_line(self, text: str) -> None:
        """Send one line to Piper. Each line is synthesised as a unit."""
        process = self._process
        if process is None or process.stdin is None:
            raise TTSError("Piper is not running; call start() first")
        if process.poll() is not None:
            raise TTSError(f"Piper exited with code {process.returncode}")

        try:
            process.stdin.write(text.encode("utf-8") + b"\n")
            process.stdin.flush()
        except OSError as exc:
            raise TTSError(f"Could not send text to Piper: {exc}") from exc

        with self._output_lock:
            self._last_output = time.perf_counter()

    def _drain_stdout(self) -> None:
        """Move audio from Piper to the speaker. Runs on its own thread."""
        process = self._process
        if process is None or process.stdout is None:
            return

        while True:
            try:
                chunk = process.stdout.read(READ_CHUNK_BYTES)
            except (OSError, ValueError):
                return
            if not chunk:
                return

            with self._output_lock:
                self._last_output = time.perf_counter()
                self._audio_bytes += len(chunk)

            if not self._interrupted.is_set() and not self._discard.is_set():
                self._player.write(chunk)

    def _await_idle(self, timeout: float = SPEAK_TIMEOUT_SECONDS) -> bool:
        """Wait until Piper has produced audio and then gone quiet.

        Both halves are necessary. Watching only for a gap would observe the
        silence *before* synthesis starts and conclude the utterance was over,
        cutting Bruno off before its first word.

        Returns:
            True if synthesis completed, False if it timed out.
        """
        if not self._await_first_audio():
            return False

        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if self._interrupted.is_set():
                return True
            with self._output_lock:
                quiet_for = time.perf_counter() - self._last_output
            if quiet_for >= IDLE_GAP_SECONDS:
                return True
            time.sleep(0.02)

        logger.warning("Timed out waiting for %s to finish", self.name)
        return False

    def _await_first_audio(self) -> bool:
        """Block until the current utterance produces its first bytes."""
        deadline = time.perf_counter() + FIRST_AUDIO_TIMEOUT_SECONDS
        while time.perf_counter() < deadline:
            if self._interrupted.is_set():
                return True
            with self._output_lock:
                if self._audio_bytes > 0:
                    return True
            time.sleep(0.005)

        logger.warning("%s produced no audio", self.name)
        return False
