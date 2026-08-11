"""Bruno's conversational state.

A single enum with an observer hook, kept separate from the pipeline so that
a console script, a tray icon, and a future overlay can all reflect the same
state without the pipeline knowing any of them exist.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class State(Enum):
    """What Bruno is doing right now."""

    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()


StateListener = Callable[[State], None]


class StateMachine:
    """Holds the current state and notifies listeners when it changes.

    Listeners run on whichever thread caused the transition, so they must be
    fast and must not raise. An exception in one listener is logged and the
    rest still run.
    """

    def __init__(self) -> None:
        self._state = State.IDLE
        self._lock = threading.Lock()
        self._listeners: list[StateListener] = []

    @property
    def current(self) -> State:
        """The current state."""
        with self._lock:
            return self._state

    def subscribe(self, listener: StateListener) -> None:
        """Register a callback invoked on every change."""
        with self._lock:
            self._listeners.append(listener)

    def transition(self, state: State) -> None:
        """Move to a new state, notifying listeners if it actually changed."""
        with self._lock:
            if state is self._state:
                return
            self._state = state
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(state)
            except Exception:  # noqa: BLE001 -- a bad listener must not break Bruno
                logger.exception("State listener failed for %s", state.name)
