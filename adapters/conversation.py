"""In-session conversation state.

This is not the long-term memory listed as a future feature. Nothing here is
written to disk or survives the process: it exists so that "explain that
again" or "why?" refers to something, which is the difference between a
conversation and a series of unrelated questions.

History is bounded by turns rather than tokens. Token counting would need a
tokeniser per provider for a limit that conversational replies rarely
approach, and a fixed turn count keeps request latency predictable.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from typing import Final

from core.protocols import Message, Role

DEFAULT_MAX_TURNS: Final = 12


class Conversation:
    """A bounded, in-memory dialogue history.

    Args:
        system_prompt: Instructions that always lead the message list. Held
            separately from the history so that it is never evicted.
        max_turns: How many user and assistant messages to retain. The oldest
            are dropped first.
    """

    def __init__(self, system_prompt: str, *, max_turns: int = DEFAULT_MAX_TURNS) -> None:
        self._system = Message("system", system_prompt)
        self._turns: deque[Message] = deque(maxlen=max_turns)

    def add(self, role: Role, content: str) -> None:
        """Append a turn, evicting the oldest if the history is full."""
        self._turns.append(Message(role, content))

    def messages(self) -> list[Message]:
        """The full message list to send to a provider, oldest first."""
        return [self._system, *self._turns]

    def rollback(self) -> bool:
        """Drop a trailing user turn that was never answered.

        A turn that fails leaves the question in the history with no reply. One
        of those is harmless; several in a row are not. The history becomes a
        run of consecutive user messages, which is a shape models handle badly
        -- and once Bruno started failing, every later question made it worse,
        so a single bad turn turned into a conversation that never recovered.

        Returns:
            True if a message was removed.
        """
        if self._turns and self._turns[-1].role == "user":
            self._turns.pop()
            return True
        return False

    def clear(self) -> None:
        """Forget everything said so far, keeping the system prompt."""
        self._turns.clear()

    def __len__(self) -> int:
        return len(self._turns)

    def __iter__(self) -> Iterator[Message]:
        return iter(self._turns)
