"""The services Bruno can think with, and what each one is good for.

Every entry here speaks the OpenAI chat completions protocol, which is why
adding one is a table row rather than a module. What differs between them is
not the API but the economics: each has its own free allowance, measured
differently, and exhausting one says nothing about the others.

That is the entire reason this file exists. A single free tier is a hard
ceiling -- one afternoon of real use runs Groq's hundred thousand daily tokens
out, and Bruno then goes quiet until tomorrow. Three tiers used in order is not a
trick; it is three services each used exactly as offered.

Order matters and is by speed. Groq answers first tokens in roughly 300 ms,
which is what makes Bruno feel like a conversation rather than a form submission.
The others are there for when it is spent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """One service Bruno can use.

    Attributes:
        name: Short identifier, used for settings and the credential store.
        label: How to say it out loud or in a dialog.
        base_url: OpenAI-compatible API root.
        model: Conversation model. Also decides when to use a tool, so it
            wants to be the most capable one the service offers cheaply.
        vision_model: Model for requests carrying an image, or empty when the
            service cannot see. A provider that cannot see is not useless --
            it still handles every other turn.
        key_url: Where a user gets a key.
        signup_note: What to tell someone deciding whether to bother.
        reasoning_effort: Sent with vision requests when set. See
            :mod:`bruno.llm.thinking` for why this matters.
        tool_results_as_text: Report tool results as conversation rather than
            as formal tool messages, for services that will not accept their
            own tool call played back to them.
    """

    name: str
    label: str
    base_url: str
    model: str
    key_url: str
    signup_note: str
    fallback_models: tuple[str, ...] = ()
    vision_model: str = ""
    reasoning_effort: str = ""
    tool_results_as_text: bool = False

    @property
    def models(self) -> tuple[str, ...]:
        """Every model to try on this service, best first."""
        return (self.model, *self.fallback_models)

    @property
    def env_var(self) -> str:
        """Environment variable holding this provider's key."""
        return f"{self.name.upper()}_API_KEY"

    @property
    def can_see(self) -> bool:
        """Whether this service can be shown a screenshot."""
        return bool(self.vision_model)


GROQ: Final = ProviderSpec(
    name="groq",
    label="Groq",
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.3-70b-versatile",
    # Groq meters each model separately -- its own error names the model, not
    # the account -- so a spent allowance on the best one says nothing about
    # the others. These are the same key and the same service, simply not the
    # same daily bucket, and reaching for them turns "out of free usage until
    # tomorrow" into "answering slightly less well for a while".
    fallback_models=("openai/gpt-oss-120b", "llama-3.1-8b-instant"),
    # The one Groq model that both sees and calls tools. Used only for the
    # request that carries a screenshot, which costs no extra round trip: such
    # a turn already makes two requests and only the second needs eyes.
    vision_model="qwen/qwen3.6-27b",
    # That model deliberates before answering unless told not to. Asked what
    # two plus two was, it produced two hundred and fifteen words of reasoning
    # before saying "four" -- silence the user sits through.
    reasoning_effort="none",
    key_url="https://console.groq.com/keys",
    signup_note="Free, no card. About a hundred thousand tokens a day.",
)

CEREBRAS: Final = ProviderSpec(
    name="cerebras",
    label="Cerebras",
    base_url="https://api.cerebras.ai/v1",
    model="gpt-oss-120b",
    # No vision, which is fine: it covers ordinary conversation and the chain
    # falls through to something that can see.
    vision_model="",
    key_url="https://cloud.cerebras.ai",
    # The free tier is generous but the key has to come from a Personal
    # account. A key made under a Team organisation validates, lists models
    # happily, and then refuses every generation with "payment required" --
    # which reads as the service being paid rather than the key being the
    # wrong kind. See _explain_payment_required in bruno.llm.factory.
    signup_note=(
        "Free, no card: about a million tokens a day, text only. Make the key "
        "on your Personal account -- a Team one needs a subscription."
    ),
)

GEMINI: Final = ProviderSpec(
    name="gemini",
    label="Google Gemini",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    model="gemini-3.6-flash",
    # Sees and calls tools in one model, so no split is needed here.
    vision_model="gemini-3.6-flash",
    # Gemini rejects its own tool call played back through the OpenAI-compatible
    # layer: it wants a "thought_signature" that this API has no way to carry.
    # The failure lands *after* the tool has run, so a browser opened and Bruno
    # then said nothing at all.
    tool_results_as_text=True,
    key_url="https://aistudio.google.com/apikey",
    signup_note=(
        "Free with a Google account. Counted in requests rather than tokens, "
        "but the daily allowance is small -- tens of requests, not thousands."
    ),
)

# Preference order, and the ordering rule is not "largest allowance first".
#
# Services that can see the screen come before ones that cannot, so that the
# ability to answer "what am I looking at" survives as long as there is any
# allowance left anywhere. Cerebras has ten times Groq's daily tokens and still
# goes last, because spending it first would mean losing vision while a
# perfectly good vision allowance sat unused.
#
# Within that, fastest first: Groq returns a first token in roughly 300 ms,
# which is what makes Bruno feel like a conversation rather than a form.
ALL: Final[tuple[ProviderSpec, ...]] = (GROQ, GEMINI, CEREBRAS)
BY_NAME: Final[dict[str, ProviderSpec]] = {spec.name: spec for spec in ALL}

DEFAULT: Final = GROQ


def get(name: str) -> ProviderSpec | None:
    """Look up a provider by name, case-insensitively."""
    return BY_NAME.get(name.strip().lower())


def names() -> list[str]:
    """Every known provider name, in preference order."""
    return [spec.name for spec in ALL]
