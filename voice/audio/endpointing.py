"""Detects when someone starts and stops speaking.

Push-to-talk needs none of this: holding the key says "I am talking" and
releasing it says "I am done". Hands-free mode has to infer both, and both
mistakes are conspicuous. Ending too early cuts a sentence in half; ending too
late leaves a pause that makes Bruno feel slow.

Uses the Silero VAD model that ships with faster-whisper, so no extra
dependency and no extra download. That model expects finished audio rather
than a live stream, so frames are batched and evaluated in small groups.

Two guards do most of the work. A brief noise -- a cough, a door -- must not
count as speech, so a minimum run of voiced frames is required before an
utterance begins. And people pause mid-thought, so the silence that ends an
utterance is measured in hundreds of milliseconds rather than frames.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Final

import numpy as np

logger = logging.getLogger(__name__)

# Silero operates on fixed 512-sample frames at 16 kHz: 32 ms each.
FRAME_SAMPLES: Final = 512
FRAME_MS: Final = 32

DEFAULT_THRESHOLD: Final = 0.5
DEFAULT_MIN_SPEECH_MS: Final = 160
DEFAULT_SILENCE_MS: Final = 800
DEFAULT_MAX_UTTERANCE_MS: Final = 30_000


class SpeechEvent(Enum):
    """A transition detected in the audio stream."""

    STARTED = auto()
    ENDED = auto()


class SpeechEndpointer:
    """Turns a stream of audio blocks into speech start and end events.

    Args:
        threshold: Probability above which a frame counts as speech. Raise it
            in a noisy room, lower it for a quiet talker.
        min_speech_ms: Voiced audio required before an utterance is declared
            started, which rejects coughs and keyboard noise.
        silence_ms: Quiet required to end an utterance. Below roughly 600 ms
            Bruno interrupts people who pause to think; much above 1000 ms and it
            feels sluggish.
        max_utterance_ms: Hard stop, so a noisy microphone cannot record
            indefinitely.
    """

    def __init__(
        self,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        min_speech_ms: int = DEFAULT_MIN_SPEECH_MS,
        silence_ms: int = DEFAULT_SILENCE_MS,
        max_utterance_ms: int = DEFAULT_MAX_UTTERANCE_MS,
    ) -> None:
        self._threshold = threshold
        self._min_speech_frames = max(1, min_speech_ms // FRAME_MS)
        self._silence_frames = max(1, silence_ms // FRAME_MS)
        self._max_frames = max_utterance_ms // FRAME_MS

        self._model = None
        self._pending = np.empty(0, dtype=np.float32)
        self._voiced_run = 0
        self._quiet_run = 0
        self._frames_in_utterance = 0
        self._in_speech = False

    def load(self) -> None:
        """Load the VAD model. Idempotent, and safe to call at startup."""
        if self._model is not None:
            return
        from faster_whisper.vad import get_vad_model

        self._model = get_vad_model()
        logger.debug("Silero VAD loaded")

    def reset(self) -> None:
        """Forget all state, as when hands-free mode is toggled on."""
        self._pending = np.empty(0, dtype=np.float32)
        self._voiced_run = 0
        self._quiet_run = 0
        self._frames_in_utterance = 0
        self._in_speech = False

    @property
    def in_speech(self) -> bool:
        """Whether an utterance is currently in progress."""
        return self._in_speech

    def feed(self, block: np.ndarray) -> list[SpeechEvent]:
        """Process one block of audio.

        Args:
            block: Mono float32 samples at 16 kHz. Any length; frames are
                buffered across calls.

        Returns:
            Events detected in this block, in order. Usually empty.
        """
        if self._model is None:
            self.load()

        self._pending = np.concatenate((self._pending, block))
        frame_count = len(self._pending) // FRAME_SAMPLES
        if frame_count == 0:
            return []

        usable = frame_count * FRAME_SAMPLES
        chunk, self._pending = self._pending[:usable], self._pending[usable:]

        # Evaluated as one batch so the model's recurrent state carries across
        # the frames rather than resetting between each.
        probabilities = np.asarray(self._model(chunk)).reshape(-1)
        return [
            event
            for probability in probabilities
            if (event := self._step(float(probability))) is not None
        ]

    def _step(self, probability: float) -> SpeechEvent | None:
        """Advance the state machine by one frame."""
        voiced = probability >= self._threshold

        if not self._in_speech:
            self._voiced_run = self._voiced_run + 1 if voiced else 0
            if self._voiced_run >= self._min_speech_frames:
                self._in_speech = True
                self._quiet_run = 0
                self._frames_in_utterance = self._voiced_run
                return SpeechEvent.STARTED
            return None

        self._frames_in_utterance += 1
        self._quiet_run = 0 if voiced else self._quiet_run + 1

        if self._quiet_run >= self._silence_frames:
            self._end()
            return SpeechEvent.ENDED

        if self._frames_in_utterance >= self._max_frames:
            logger.info("Utterance hit the length limit; ending it")
            self._end()
            return SpeechEvent.ENDED

        return None

    def _end(self) -> None:
        self._in_speech = False
        self._voiced_run = 0
        self._quiet_run = 0
        self._frames_in_utterance = 0
