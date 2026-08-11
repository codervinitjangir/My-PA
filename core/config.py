"""Typed application settings, loaded once from the environment.

Settings are read from ``.env`` (git-ignored) or real environment variables,
parsed and validated in one place, and then passed explicitly to the components
that need them. Nothing reaches for ``os.environ`` at call time -- a module
that needs a value declares it as a constructor argument instead, which keeps
components testable and makes the full configuration surface visible here.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from core import paths

logger = logging.getLogger(__name__)

_TRUTHY: Final = frozenset({"1", "true", "yes", "on"})
_FALSY: Final = frozenset({"0", "false", "no", "off"})


def _get_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_optional_str(name: str) -> str | None:
    return _get_str(name) or None


def _get_float(name: str, default: float) -> float:
    raw = _get_str(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using default %s", name, raw, default)
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = _get_str(name).lower()
    if not raw:
        return default
    if raw in _TRUTHY:
        return True
    if raw in _FALSY:
        return False
    logger.warning("%s=%r is not a boolean; using default %s", name, raw, default)
    return default


def _read_api_keys() -> dict[str, str]:
    """Collect provider credentials from the environment.

    Imported here rather than at module scope: the provider table imports
    nothing from configuration, and keeping it that way avoids a cycle.
    """
    from adapters import providers

    found = {spec.name: _get_str(spec.env_var) for spec in providers.ALL}
    return {name: key for name, key in found.items() if key}


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything Bruno's behaviour can be tuned by.

    Attributes:
        llm_provider: Which service Bruno prefers. Others with a stored key are
            tried after it when its free allowance runs out.
        llm_model: Model identifier, or empty for the provider's default.
            Providers retire models periodically, so this is overridable
            without a code change. Applies to the preferred provider only.
        api_keys: Credentials found in the environment, keyed by provider
            name. Empty entries are omitted, so presence means usable.
        input_device: Substring matched against microphone names. ``None``
            selects the operating system default.
        output_device: Substring matched against speaker names.
        always_on_mic: Keep the microphone stream open and maintain a short
            pre-roll buffer, so the first word is never clipped. Disable to
            open the device only while the hotkey is held, which is stricter
            but costs 100-300 ms of device startup on every interaction.
        device: Where speech recognition runs. ``auto`` uses the GPU only when
            both a CUDA device and the cuDNN runtime are present; ``cpu`` and
            ``cuda`` force the choice.
        voice: Piper voice name, matching a file in ``voices/``.
        speech_speed: Length scale for synthesis. Above 1.0 is slower.
        silence_ms: Pause that ends a turn in hands-free mode. Below roughly
            600 ms Bruno interrupts people who stop to think; much above 1000 ms
            and it feels sluggish.
        vad_threshold: Speech probability required to count as talking. Raise
            it in a noisy room, lower it for a quiet microphone.
        allow_screen: Whether Bruno may look at the screen when a question needs
            it. Off means the capability is never offered to the model at all,
            rather than offered and refused -- there is nothing to go wrong.
        allow_browser: Whether Bruno may open pages and scroll the browser the
            user already has open. It never clicks anything, and it acts only
            on a window that is already in front.
        show_orb: Whether to float the animated orb on screen while Bruno
            is listening, thinking, or speaking.
        vision_model: Model used only for requests carrying a screenshot.
            Blank uses the provider's default. Kept separate from
            ``llm_model`` because the best conversationalist and the model
            that can see are rarely the same one.
        reasoning: How hard the model should think before answering, for models
            that support it. Blank uses the provider's default for its model.
            Thinking is latency the user hears as silence, so Bruno turns it off
            where it can; this exists to put it back when a model needs it.
        log_level: Root logging level name.
    """

    llm_provider: str = "groq"
    llm_model: str = ""
    api_keys: Mapping[str, str] = field(default_factory=dict)
    input_device: str | None = None
    output_device: str | None = None
    always_on_mic: bool = True
    device: str = "auto"
    voice: str = "en_GB-alan-medium"
    speech_speed: float = 1.0
    silence_ms: int = 800
    vad_threshold: float = 0.5
    allow_screen: bool = True
    allow_browser: bool = True
    show_orb: bool = True
    vision_model: str = ""
    reasoning: str = ""
    log_level: str = "INFO"


def load_settings(env_file: Path | None = None) -> Settings:
    """Read settings from ``.env`` and the process environment.

    Real environment variables win over ``.env`` entries, which is what makes
    per-run overrides and CI configuration work.

    Args:
        env_file: Location of the dotenv file. Defaults to ``.env`` at the
            repository root, which exists only in a source checkout -- a
            packaged install is configured through setup and the tray menu.

    Returns:
        An immutable settings object.
    """
    path = env_file or paths.env_file()
    if path.is_file():
        load_dotenv(path, override=False)
    else:
        logger.debug("No .env file at %s; using environment and defaults", path)

    return Settings(
        llm_provider=_get_str("BRUNO_LLM_PROVIDER", "groq").lower(),
        llm_model=_get_str("BRUNO_LLM_MODEL"),
        api_keys=_read_api_keys(),
        input_device=_get_optional_str("BRUNO_INPUT_DEVICE"),
        output_device=_get_optional_str("BRUNO_OUTPUT_DEVICE"),
        always_on_mic=_get_bool("BRUNO_ALWAYS_ON_MIC", default=True),
        device=_get_str("BRUNO_DEVICE", "auto").lower(),
        voice=_get_str("BRUNO_VOICE", "en_US-norman-medium"),
        speech_speed=_get_float("BRUNO_SPEECH_SPEED", 1.0),
        silence_ms=int(_get_float("BRUNO_SILENCE_MS", 800)),
        vad_threshold=_get_float("BRUNO_VAD_THRESHOLD", 0.5),
        allow_screen=_get_bool("BRUNO_ALLOW_SCREEN", default=True),
        allow_browser=_get_bool("BRUNO_ALLOW_BROWSER", default=True),
        show_orb=_get_bool("BRUNO_SHOW_ORB", default=True),
        vision_model=_get_str("BRUNO_VISION_MODEL"),
        reasoning=_get_str("BRUNO_REASONING"),
        log_level=_get_str("BRUNO_LOG_LEVEL", "INFO").upper(),
    )
