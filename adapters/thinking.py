"""Removing chain-of-thought from a reply before it is spoken.

Reasoning models narrate their working inside ``<think>`` tags and then give
the answer. Read on a screen that is a curiosity; read aloud it is a disaster.
Asked "what's two plus two", one such model produced two hundred and fifteen
words of deliberation -- including a literal ``</think>`` and a tick emoji --
before the word "four".

The provider disables reasoning where the API allows it, which is faster than
hiding it because the tokens are never generated. This exists because that
switch is model-specific and cannot be relied on: a different model, a new
version, or a provider that ignores the parameter would otherwise send Bruno's
internal monologue to the speakers.

Filtering has to survive streaming, where a tag arrives in pieces and
``<thi`` at the end of one chunk is completed by ``nk>`` in the next. So any
trailing text that could still become a tag is held back rather than emitted,
which costs a few characters of delay and never leaks a partial tag.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from typing import Final

logger = logging.getLogger(__name__)

OPEN: Final = "<think>"
CLOSE: Final = "</think>"


def _held_prefix(text: str, tag: str) -> int:
    """Length of the trailing part of ``text`` that could still become ``tag``.

    ``"...and <thi"`` against ``"<think>"`` returns 4, so those characters are
    kept back until the next fragment settles whether they open a tag or are
    ordinary text that happens to look like one.
    """
    longest = min(len(tag) - 1, len(text))
    for size in range(longest, 0, -1):
        if text.endswith(tag[:size]):
            return size
    return 0


def strip_thinking(fragments: Iterable[str]) -> Iterator[str]:
    """Yield a fragment stream with ``<think>`` blocks removed.

    An unclosed block is dropped entirely: a reply cut off mid-thought has no
    answer in it, and speaking the reasoning would be worse than silence.

    Args:
        fragments: Text chunks as the model produced them.

    Yields:
        The same text, minus any reasoning and minus the tags themselves.
    """
    buffer = ""
    inside = False
    dropped = 0

    for fragment in fragments:
        buffer += fragment

        while buffer:
            if inside:
                end = buffer.find(CLOSE)
                if end < 0:
                    # Still thinking. Keep only what might be a partial closing
                    # tag; everything else is monologue and goes nowhere.
                    keep = _held_prefix(buffer, CLOSE)
                    dropped += len(buffer) - keep
                    buffer = buffer[len(buffer) - keep :] if keep else ""
                    break

                dropped += end
                buffer = buffer[end + len(CLOSE) :]
                inside = False
                continue

            start = buffer.find(OPEN)
            if start < 0:
                held = _held_prefix(buffer, OPEN)
                emit, buffer = buffer[: len(buffer) - held], buffer[len(buffer) - held :]
                if emit:
                    yield emit
                break

            if start:
                yield buffer[:start]
            buffer = buffer[start + len(OPEN) :]
            inside = True

    if inside:
        logger.warning("Reply ended inside a reasoning block; dropped %d characters", dropped)
        return

    if buffer:
        yield buffer

    if dropped:
        logger.info("Removed %d characters of reasoning before speaking", dropped)
