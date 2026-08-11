"""Falling through to the next service when one stops answering.

A free tier is a cliff, not a slope. Groq's allowance lasts an afternoon of
real use and then every request fails identically until the next day -- Bruno
holds a conversation, then abruptly cannot, with nothing wrong on the user's
side and nothing they can do about it.

This tries each configured service in turn. Any failure on the first moves to
the second, which is deliberately broader than only moving on quota errors: a
service that cannot see an image, or is briefly down, or has retired the model
we asked for, is equally a reason to ask someone else. Distinguishing those
would mean enumerating every way a service can decline, and getting that list
wrong means silence.

One rule governs the whole design: **once a fragment has been spoken, there is
no falling through.** The user is already hearing an answer, and starting a
second one over the top of it is worse than the failure. A provider that dies
mid-sentence fails the turn.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Sequence
from typing import Final

from core.protocols import (
    LLMAuthError,
    LLMError,
    LLMProvider,
    LLMQuotaError,
    LLMRateLimitError,
    Message,
    Toolbox,
)

logger = logging.getLogger(__name__)

# How long a provider is skipped after saying it has nothing left. Without
# this, every single turn pays a failed round trip to each exhausted service
# before reaching one that works -- seconds of silence added to every reply,
# and a request spent against a limit that is already blown.
COOLDOWN_SECONDS: Final = 60.0

# For failures that will not heal on their own. A rejected key and a bill to
# pay are the same the second time as the first, so retrying them once a
# minute only adds a failed round trip to every reply.
LONG_COOLDOWN_SECONDS: Final = 900.0

# Substrings identifying a refusal that needs a human, not a wait.
_UNPAID_MARKERS: Final = ("402", "payment_required", "payment required")


def _cooldown_for(exc: LLMError) -> float:
    """How long to leave a provider alone after this failure.

    Zero means try it again on the next turn: a dropped connection or a
    one-off server error says nothing about the next request.
    """
    if isinstance(exc, LLMAuthError) or any(
        marker in str(exc).lower() for marker in _UNPAID_MARKERS
    ):
        return LONG_COOLDOWN_SECONDS
    if isinstance(exc, LLMQuotaError):
        return LONG_COOLDOWN_SECONDS
    if isinstance(exc, LLMRateLimitError):
        return COOLDOWN_SECONDS
    return 0.0


class ProviderChain:
    """Tries several providers in order. Satisfies :class:`LLMProvider`.

    Args:
        providers: Services to try, best first. A single-element chain behaves
            exactly like the provider it holds.

    Raises:
        ValueError: If no providers are given, which is a wiring mistake
            rather than a runtime condition.
    """

    def __init__(self, providers: Sequence[LLMProvider]) -> None:
        if not providers:
            raise ValueError("A provider chain needs at least one provider")
        self._providers = tuple(providers)
        self._resting: dict[int, tuple[float, LLMError]] = {}

    @property
    def name(self) -> str:
        """Every provider in order, for logs and diagnostics."""
        return " then ".join(provider.name for provider in self._providers)

    @property
    def primary(self) -> LLMProvider:
        """The provider tried first."""
        return self._providers[0]

    def __len__(self) -> int:
        return len(self._providers)

    def stream_reply(
        self, messages: Sequence[Message], tools: Toolbox | None = None
    ) -> Iterator[str]:
        """Generate a reply, moving to the next provider if one fails.

        Yields:
            Text fragments from whichever provider answered.

        Raises:
            LLMError: If every provider failed. The *preferred* provider's
                failure is raised rather than the last one: the chain is in
                preference order, so the first is the service the user is
                actually relying on. Hearing "I'm out of Groq for today" is
                useful; hearing that the third service wants a credit card is
                not, and it was the one spoken because it happened to fail
                last.
        """
        # Keyed by position so the preferred provider's failure can be found
        # again, including when it was skipped rather than tried. Without that,
        # resting the first two services meant the only error left to report
        # came from the third -- and a user out of Groq for the day was told
        # that a service they had never heard of wanted a credit card.
        errors: dict[int, LLMError] = {}

        for position, provider in enumerate(self._providers):
            resting = self._why_resting(position)
            if resting is not None:
                errors[position] = resting
                continue

            spoken = False
            try:
                for fragment in provider.stream_reply(messages, tools):
                    spoken = True
                    yield fragment
                self._resting.pop(position, None)
                return
            except LLMError as exc:
                if spoken:
                    # Half an answer is already on its way to the speaker.
                    # Starting another over the top of it is worse than
                    # stopping here.
                    logger.error("%s failed mid-reply: %s", provider.name, exc)
                    raise

                errors[position] = exc
                self._rest(position, exc)

                remaining = len(self._providers) - position - 1
                logger.warning(
                    "%s failed (%s); %s",
                    provider.name,
                    exc,
                    f"trying {remaining} more" if remaining else "nothing left to try",
                )

        # The lowest position is the most preferred service, so its failure is
        # the one the user can actually act on.
        raise errors[min(errors)]

    # -- cooldown -----------------------------------------------------------

    def _why_resting(self, position: int) -> LLMError | None:
        """The failure a provider is still sitting out, if it is."""
        entry = self._resting.get(position)
        if entry is None:
            return None

        until, error = entry
        if time.monotonic() >= until:
            del self._resting[position]
            return None
        return error

    def _rest(self, position: int, error: LLMError) -> None:
        """Stop asking a provider for a while, remembering why."""
        seconds = _cooldown_for(error)
        if not seconds:
            return

        self._resting[position] = (time.monotonic() + seconds, error)
        logger.info(
            "Resting %s for %.0fs", self._providers[position].name, seconds
        )

    def warm_up(self) -> bool:
        """Open connections to every provider.

        All of them, not just the first: the whole point of a fallback is that
        it is reached at the moment something has already gone wrong, and
        paying a cold connection's second of setup right then would land that
        delay on a user who has just been kept waiting once already.

        Returns:
            True if any provider was reachable.
        """
        warmed = False
        for provider in self._providers:
            try:
                warmed |= bool(provider.warm_up())
            except Exception:  # noqa: BLE001 -- warming is an optimisation
                logger.debug("Warm-up failed for %s", provider.name, exc_info=True)
        return warmed
