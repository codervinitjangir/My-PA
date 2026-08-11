"""Groq, Bruno's default language model provider.

Chosen for latency rather than reasoning quality. Groq's custom silicon returns
a first token in roughly 300 ms where conventional GPU inference takes over a
second, and time-to-first-token is what governs how long Bruno stays silent after
you stop speaking. Everything after that streams faster than speech, so it
costs nothing.
"""

from __future__ import annotations

from typing import Final

from adapters.openai_compatible import OpenAICompatibleProvider

BASE_URL: Final = "https://api.groq.com/openai/v1"

# Two models, because no single Groq model is best at both jobs.
#
# The conversation model does almost all the work: it talks, and it decides
# when a question needs the screen. Both are things a large instruction-following
# model does markedly better. Running the whole product on the smaller vision
# model was tried and was worse in exactly the two ways that matter -- it
# talked less well, and it missed screen questions unless they used the literal
# word "screen", then told the user it could not see at all.
DEFAULT_MODEL: Final = "llama-3.3-70b-versatile"

# Used only for the request that actually carries a screenshot. This costs no
# extra round trip: a turn that looks at the screen already makes two requests,
# and only the second one needs eyes.
VISION_MODEL: Final = "qwen/qwen3.6-27b"

# The vision model reasons before answering unless told not to, and reasoning
# is worse than useless here. Asked "what is two plus two" it produced two
# hundred and fifteen words of deliberation -- ending in a tick emoji and a
# literal closing tag -- before saying "four". Every one of those tokens is
# silence the user sits through. "none" skips the thinking entirely rather than
# generating and hiding it.
VISION_REASONING_EFFORT: Final = "none"


def create(
    api_key: str,
    model: str = DEFAULT_MODEL,
    vision_model: str = VISION_MODEL,
    reasoning: str = "",
) -> OpenAICompatibleProvider:
    """Build a provider pointed at Groq.

    Args:
        api_key: Key from https://console.groq.com/keys.
        model: Conversation model. Providers retire these periodically; use
            ``available_models`` on the result to see what is currently valid.
        vision_model: Model for requests carrying images.
        reasoning: Overrides :data:`VISION_REASONING_EFFORT`. Blank keeps it.

    Returns:
        A configured provider.
    """
    return OpenAICompatibleProvider(
        api_key=api_key,
        model=model,
        base_url=BASE_URL,
        label="groq",
        vision_model=vision_model,
        vision_reasoning_effort=reasoning or VISION_REASONING_EFFORT,
    )
