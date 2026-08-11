"""Builds the language model provider from configuration and stored keys.

The single place in Bruno that knows which services exist. Everything else
depends only on :class:`~bruno.core.protocols.LLMProvider`, so a chain of three
services and a single one are indistinguishable to the pipeline.

One key is required and the rest are optional, deliberately. Demanding three
signups before Bruno says a word would undo the setup flow; but a user who runs
out of free tokens on a Tuesday afternoon should be able to add a second
service and carry on, rather than wait until tomorrow.
"""

from __future__ import annotations

import logging

from core import credentials
from core.config import Settings
from core.protocols import LLMError, LLMProvider, Message
from adapters import providers
from adapters.chain import ProviderChain
from adapters.openai_compatible import OpenAICompatibleProvider
from adapters.providers import ProviderSpec

logger = logging.getLogger(__name__)

# Kept for callers that only need to point a user at a signup page.
KEY_URLS = {spec.name: spec.key_url for spec in providers.ALL}


def resolve_key(spec: ProviderSpec, settings: Settings) -> str:
    """Find a key for one provider.

    Environment first, so a developer's ``.env`` and a one-off override both
    keep working, then the encrypted store written during setup.
    """
    from_env = settings.api_keys.get(spec.name, "")
    if from_env:
        return from_env
    return credentials.load_key(spec.name)


def configured(settings: Settings) -> list[ProviderSpec]:
    """Providers that have a key, in the order they should be tried.

    The one named in settings leads, whether or not it is Bruno's own default.
    """
    primary = providers.get(settings.llm_provider) or providers.DEFAULT
    ordered = [primary, *(spec for spec in providers.ALL if spec.name != primary.name)]
    return [spec for spec in ordered if resolve_key(spec, settings)]


def build_one(
    spec: ProviderSpec, api_key: str, settings: Settings, model: str = ""
) -> LLMProvider:
    """Construct one entry of the chain.

    Args:
        spec: Which service.
        api_key: Its credential.
        settings: For the vision and reasoning overrides.
        model: Which of the service's models this entry uses. Blank means its
            best. Choosing the model is the caller's job; see
            :func:`models_for`.
    """
    is_primary = spec.name == (settings.llm_provider or providers.DEFAULT.name)
    return OpenAICompatibleProvider(
        api_key=api_key,
        model=model or spec.model,
        base_url=spec.base_url,
        label=spec.name,
        vision_model=(
            settings.vision_model if is_primary and settings.vision_model else spec.vision_model
        ),
        vision_reasoning_effort=settings.reasoning or spec.reasoning_effort,
        tool_results_as_text=spec.tool_results_as_text,
    )


def models_for(spec: ProviderSpec, settings: Settings) -> list[str]:
    """Which models to try on one service, best first.

    A user's model override replaces the preferred service's *first* choice
    and leaves its fallbacks alone. Applied to all of them it would name a
    model the service has never heard of, and there would be nothing left to
    fall back to -- which is the whole reason the list has more than one entry.
    """
    models = list(spec.models)
    is_primary = spec.name == (settings.llm_provider or providers.DEFAULT.name)
    if is_primary and settings.llm_model:
        models[0] = settings.llm_model
    return models


def create_provider(settings: Settings, api_key: str = "") -> LLMProvider:
    """Build the chain of providers Bruno will use.

    Args:
        settings: Loaded application settings.
        api_key: Key for the primary provider, overriding what is stored.
            Supplied by onboarding, which resolves the environment and the
            encrypted store before Bruno starts.

    Returns:
        A single provider, or a chain that falls through as allowances run out.

    Raises:
        LLMError: If no provider has a usable key.
    """
    specs = configured(settings)
    primary = providers.get(settings.llm_provider) or providers.DEFAULT

    if api_key and primary not in specs:
        # Onboarding has just obtained a key that is not stored yet.
        specs.insert(0, primary)

    if not specs:
        raise LLMError(
            f"No API key for {primary.label}. Run Bruno once interactively, or set "
            f"{primary.env_var}."
        )

    # One entry per model per service. A service's allowance is usually
    # metered per model, so its second-best model is a genuinely separate
    # bucket rather than the same wall a second time.
    built: list[LLMProvider] = []
    for spec in specs:
        key = api_key if spec.name == primary.name and api_key else resolve_key(spec, settings)
        built.extend(
            build_one(spec, key, settings, model) for model in models_for(spec, settings)
        )

    chain = ProviderChain(built)
    if len(chain) == 1:
        logger.info("Using %s", chain.primary.name)
    else:
        logger.info("Using %s", chain.name)
    return chain


def validate_key(provider_name: str, api_key: str) -> str:
    """Check a key against the live service.

    A typed key must fail here, immediately and with an explanation, rather
    than three minutes later when Bruno mysteriously will not answer.

    Args:
        provider_name: Which provider the key belongs to.
        api_key: The key to test.

    Returns:
        An empty string if the key works, otherwise a message to show the user.
    """
    spec = providers.get(provider_name)
    if spec is None:
        return f"I do not know a provider called {provider_name!r}."

    probe = OpenAICompatibleProvider(
        api_key=api_key, model=spec.model, base_url=spec.base_url, label=spec.name
    )
    try:
        probe.available_models()
    except LLMError as exc:
        return _explain(exc, spec)

    # Listing models is not proof the key can generate. A Cerebras key made
    # under a Team organisation lists happily and then refuses every request
    # with "payment required", so the only honest check is to generate.
    try:
        for _fragment in probe.stream_reply([Message("user", "hi")]):
            break
    except LLMError as exc:
        return _explain(exc, spec)
    return ""


def _explain(exc: LLMError, spec: ProviderSpec) -> str:
    """Turn a provider's refusal into something the user can act on."""
    message = str(exc)

    if "401" in message or "invalid_api_key" in message or "Unauthorized" in message:
        return "That key was rejected. Check you copied all of it."

    if "402" in message or "payment_required" in message:
        # Almost always the wrong kind of account rather than a real bill.
        return (
            f"{spec.label} accepted the key but will not run anything on it. "
            "This usually means the key belongs to a Team organisation, which "
            "needs a subscription. Make a new key on your Personal account "
            f"at {spec.key_url} and try that one."
        )

    if "403" in message or "PERMISSION_DENIED" in message:
        return "That key was refused. Check the API is enabled for it."

    if "429" in message or "rate limit" in message.lower():
        return (
            f"{spec.label} says this key is already at its limit. The key is "
            "fine; try again in a few minutes."
        )

    if "Connection" in message or "timed out" in message:
        return f"Could not reach {spec.label}. Check your internet connection."

    return message
