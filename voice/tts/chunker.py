"""Turns a stream of text fragments into complete sentences.

The sentence is the unit that makes Bruno feel responsive. A language model emits
fragments a few characters at a time; a synthesiser needs a whole sentence to
produce natural intonation. Splitting on sentence boundaries is what lets Bruno
speak its opening line while the rest of the reply is still being written.

The first sentence is deliberately allowed to be short. Waiting for a well
formed opening clause would add its entire generation time to the silence
before Bruno makes a sound, and that silence is the thing users actually notice.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Final

# A terminator followed by whitespace. Requiring the whitespace avoids
# splitting inside "3.14", "e.g." or an ellipsis mid-thought.
_BOUNDARY: Final = re.compile(r"(?<=[.!?])\s+")

# Clause breaks, used only to get the *first* sentence out quickly.
_CLAUSE: Final = re.compile(r"(?<=[,;:])\s+")

DEFAULT_MIN_FIRST: Final = 40
DEFAULT_MAX_LENGTH: Final = 300


def split_stream(
    fragments: Iterable[str],
    *,
    min_first: int = DEFAULT_MIN_FIRST,
    max_length: int = DEFAULT_MAX_LENGTH,
) -> Iterator[str]:
    """Group text fragments into speakable sentences.

    Args:
        fragments: Arbitrary chunks of text, in order, such as those produced
            by :meth:`~bruno.core.protocols.LLMProvider.stream_reply`.
        min_first: Minimum characters before the opening chunk may be emitted
            at a clause break rather than a sentence end. Below this a break
            tends to produce a fragment too short to intone naturally.
        max_length: Emit regardless once the buffer reaches this length, so a
            reply written without punctuation still gets spoken.

    Yields:
        Sentences with surrounding whitespace removed, never empty.
    """
    buffer = ""
    is_first = True

    for fragment in fragments:
        buffer += fragment

        while True:
            chunk, buffer = _take(buffer, is_first, min_first, max_length)
            if chunk is None:
                break
            yield chunk
            is_first = False

    tail = buffer.strip()
    if tail:
        yield tail


def _take(
    buffer: str, is_first: bool, min_first: int, max_length: int
) -> tuple[str | None, str]:
    """Peel one speakable chunk off the front of the buffer.

    Returns:
        The chunk and the remaining buffer, or ``(None, buffer)`` if no
        complete chunk is available yet.
    """
    match = _BOUNDARY.search(buffer)
    if match:
        return buffer[: match.start()].strip(), buffer[match.end() :]

    # Only the opening chunk may break at a comma. Doing this throughout would
    # chop the whole reply into fragments and destroy its rhythm.
    if is_first and len(buffer) >= min_first:
        clause = _CLAUSE.search(buffer, min_first)
        if clause:
            return buffer[: clause.start()].strip(), buffer[clause.end() :]

    if len(buffer) >= max_length:
        cut = buffer.rfind(" ", 0, max_length)
        if cut > 0:
            return buffer[:cut].strip(), buffer[cut + 1 :]

    return None, buffer
