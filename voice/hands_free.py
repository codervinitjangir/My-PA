"""Hands-free conversation mode.

Push-to-talk is precise but tiring: a real conversation means holding a key
for every sentence. Toggling this on lets Bruno listen continuously, work out
when each sentence ends, answer, and keep listening.

The complication is that Bruno can hear itself. On speakers its own reply would
be detected as speech and answered, so the microphone is ignored while Bruno is
talking. Headphone users lose nothing by this; speaker users lose the ability
to interrupt by voice, and still have the hotkeys.

Detection runs on its own thread rather than the audio callback. The callback
is a realtime thread where blocking causes dropouts, and a VAD pass over a
batch of frames takes a few milliseconds -- small, but not small enough to
belong there.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Final

import numpy as np

from voice.audio.endpointing import SpeechEndpointer, SpeechEvent
from voice.audio.recorder import AudioRecorder
from core.state import State, StateMachine
from voice.pipeline import Pipeline

logger = logging.getLogger(__name__)

_SHUTDOWN: Final = None

# Bounded so that a stalled detector drops audio rather than growing without
# limit. At 30 ms per block this is about six seconds of slack.
_QUEUE_SIZE: Final = 200


class HandsFreeMode:
    """Listens continuously and submits each utterance to the pipeline.

    Args:
        recorder: Microphone capture, already started.
        pipeline: Where completed utterances are sent.
        state: Shared state, used to know when Bruno is talking.
        endpointer: Speech detector. A default is created if omitted.
    """

    def __init__(
        self,
        *,
        recorder: AudioRecorder,
        pipeline: Pipeline,
        state: StateMachine,
        endpointer: SpeechEndpointer | None = None,
    ) -> None:
        self._recorder = recorder
        self._pipeline = pipeline
        self._state = state
        self._endpointer = endpointer or SpeechEndpointer()

        self._enabled = threading.Event()
        self._blocks: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=_QUEUE_SIZE)
        self._worker: threading.Thread | None = None
        self._dropped = 0

    # -- lifecycle ----------------------------------------------------------

    def prepare(self) -> None:
        """Load the VAD model and start the detector thread.

        Called at startup so that toggling the mode on is instant. The thread
        idles until enabled.
        """
        if self._worker is not None:
            return

        self._endpointer.load()
        self._recorder.subscribe(self._on_block)
        self._worker = threading.Thread(
            target=self._run, name="ev-hands-free", daemon=True
        )
        self._worker.start()

    def close(self) -> None:
        """Stop the detector thread."""
        self._enabled.clear()
        if self._worker is not None:
            self._blocks.put(_SHUTDOWN)
            self._worker.join(timeout=3.0)
            self._worker = None

    @property
    def enabled(self) -> bool:
        """Whether Bruno is listening continuously."""
        return self._enabled.is_set()

    def toggle(self) -> bool:
        """Turn hands-free listening on or off.

        Returns:
            True if it is now enabled.
        """
        if self._enabled.is_set():
            self.disable()
        else:
            self.enable()
        return self._enabled.is_set()

    def enable(self) -> None:
        """Begin listening continuously."""
        if self._enabled.is_set():
            return
        self._endpointer.reset()
        self._drain()
        self._enabled.set()
        logger.info("Hands-free mode on")

    def disable(self) -> None:
        """Stop listening continuously and discard anything part-heard."""
        if not self._enabled.is_set():
            return
        self._enabled.clear()
        self._recorder.end_capture()
        self._endpointer.reset()
        self._drain()
        self._state.transition(State.IDLE)
        logger.info("Hands-free mode off")

    # -- audio thread -------------------------------------------------------

    def _on_block(self, block: np.ndarray) -> None:
        """Receive audio from the recorder. Realtime thread -- stay cheap."""
        if not self._enabled.is_set():
            return
        try:
            self._blocks.put_nowait(block)
        except queue.Full:
            self._dropped += 1

    def _drain(self) -> None:
        while True:
            try:
                self._blocks.get_nowait()
            except queue.Empty:
                return

    # -- detector thread ----------------------------------------------------

    def _run(self) -> None:
        while True:
            block = self._blocks.get()
            if block is _SHUTDOWN:
                return
            if not self._enabled.is_set():
                continue
            try:
                self._process(block)
            except Exception:  # noqa: BLE001 -- keep listening despite one bad block
                logger.exception("Speech detection failed")

    def _process(self, block: np.ndarray) -> None:
        """Feed one block to the detector and act on what it finds."""
        if self._is_output_active():
            # Bruno is talking or thinking. Feeding this in would either detect
            # Bruno's own voice on speakers, or start a second utterance while
            # the first is still being answered.
            if self._endpointer.in_speech:
                self._endpointer.reset()
                self._recorder.end_capture()
            return

        for event in self._endpointer.feed(block):
            if event is SpeechEvent.STARTED:
                logger.debug("Speech started")
                self._recorder.begin_capture()
                self._state.transition(State.LISTENING)
            elif event is SpeechEvent.ENDED:
                logger.debug("Speech ended")
                clip = self._recorder.end_capture()
                if clip is not None:
                    self._pipeline.submit(clip)
                else:
                    self._state.transition(State.IDLE)

    def _is_output_active(self) -> bool:
        return self._state.current in (State.THINKING, State.SPEAKING)
