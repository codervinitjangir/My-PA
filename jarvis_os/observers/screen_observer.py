"""
screen_observer.py

Responsibility: OBSERVE ONLY.
  1. Capture one screenshot (native, via PIL.ImageGrab)
  2. Sanitize to base64 in-memory
  3. Pass to VisionService
  4. Parse the text response into ScreenState

Rules:
  - NO image storage
  - NO background threads
  - NO continuous polling
  - Screenshot deleted from memory immediately after analysis
  - Cooldown: 15 seconds between captures
"""

import io
import base64
import time
import logging
import re
from typing import Optional

from jarvis_os.observers.observer_models import ScreenState, ScreenActivityType

logger = logging.getLogger("J.A.R.V.I.S")

SCREEN_ANALYZE_COOLDOWN = 15  # seconds

# ── Application → (activity, workspace_hint) mapping ─────────────────────────
_APP_MAP: dict[str, tuple[ScreenActivityType, str]] = {
    # Coding / Debugging
    "code":        (ScreenActivityType.CODING,   "dev"),
    "vscode":      (ScreenActivityType.CODING,   "dev"),
    "pycharm":     (ScreenActivityType.CODING,   "dev"),
    "terminal":    (ScreenActivityType.CODING,   "dev"),
    "powershell":  (ScreenActivityType.CODING,   "dev"),
    "cmd":         (ScreenActivityType.CODING,   "dev"),
    "github":      (ScreenActivityType.CODING,   "dev"),
    "git":         (ScreenActivityType.CODING,   "dev"),
    # Learning
    "leetcode":    (ScreenActivityType.LEARNING, "learning"),
    "youtube":     (ScreenActivityType.LEARNING, "learning"),
    "coursera":    (ScreenActivityType.LEARNING, "learning"),
    "udemy":       (ScreenActivityType.LEARNING, "learning"),
    "docs":        (ScreenActivityType.LEARNING, "learning"),
    "stackoverflow": (ScreenActivityType.LEARNING, "learning"),
    # Research
    "chatgpt":     (ScreenActivityType.RESEARCH,  "research"),
    "claude":      (ScreenActivityType.RESEARCH,  "research"),
    "gemini":      (ScreenActivityType.RESEARCH,  "research"),
    "perplexity":  (ScreenActivityType.RESEARCH,  "research"),
    "notion":      (ScreenActivityType.RESEARCH,  "research"),
    "browser":     (ScreenActivityType.RESEARCH,  "research"),
    # Job Search
    "linkedin":    (ScreenActivityType.JOB_SEARCH, "career"),
    "glassdoor":   (ScreenActivityType.JOB_SEARCH, "career"),
    "indeed":      (ScreenActivityType.JOB_SEARCH, "career"),
    # Designing
    "figma":       (ScreenActivityType.DESIGNING,  "design"),
    "canva":       (ScreenActivityType.DESIGNING,  "design"),
    # Communication
    "gmail":       (ScreenActivityType.COMMUNICATION, "career"),
    "outlook":     (ScreenActivityType.COMMUNICATION, "career"),
    "slack":       (ScreenActivityType.COMMUNICATION, "dev"),
    "teams":       (ScreenActivityType.COMMUNICATION, "general"),
    # Entertainment
    "netflix":     (ScreenActivityType.ENTERTAINMENT, "general"),
    "spotify":     (ScreenActivityType.ENTERTAINMENT, "general"),
    "discord":     (ScreenActivityType.ENTERTAINMENT, "general"),
}

_NEXT_ACTION_MAP: dict[ScreenActivityType, str] = {
    ScreenActivityType.CODING:         "Continue implementation.",
    ScreenActivityType.DEBUGGING:      "Fix the error and verify with a test.",
    ScreenActivityType.LEARNING:       "Take notes and stay focused.",
    ScreenActivityType.RESEARCH:       "Save key insights to Notion.",
    ScreenActivityType.JOB_SEARCH:     "Continue internship applications.",
    ScreenActivityType.DESIGNING:      "Refine your current design.",
    ScreenActivityType.COMMUNICATION:  "Reply and then get back to work.",
    ScreenActivityType.ENTERTAINMENT:  "You've earned a break.",
    ScreenActivityType.UNKNOWN:        "Define your next focus area.",
}

_SCREEN_PROMPT = """Analyze this screenshot and respond in EXACTLY this format (no extra text):

APPLICATION: <name of the primary application or website visible>
ACTIVITY: <one of: Coding, Debugging, Learning, Research, Job Search, Designing, Communication, Entertainment, Unknown>
TEXT_VISIBLE: <yes or no — is meaningful text or code visible?>
SUMMARY: <one sentence describing what Boss is doing>
NEXT_ACTION: <one short sentence suggesting the next best action>

Do not include any other text. Use plain text only."""


class ScreenObserver:
    def __init__(self):
        self._last_analyzed: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def capture_screen(self) -> Optional[bytes]:
        """
        Check cooldown, then capture a single screenshot in-memory.
        Returns raw PNG bytes, or None if still in cooldown.
        """
        elapsed = time.time() - self._last_analyzed
        if elapsed < SCREEN_ANALYZE_COOLDOWN:
            remaining = int(SCREEN_ANALYZE_COOLDOWN - elapsed)
            raise CooldownError(
                f"Please wait {remaining} more second(s) before analyzing again."
            )

        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            raw_bytes = buf.getvalue()
            buf.close()
            img.close()
            logger.info("[SCREEN] Screenshot captured (%d bytes).", len(raw_bytes))
            return raw_bytes
        except ImportError:
            raise RuntimeError(
                "Pillow is not installed. Run: pip install Pillow"
            )
        except Exception as e:
            logger.warning("[SCREEN] Capture failed: %s", e)
            raise

    def sanitize_data(self, image_bytes: bytes) -> str:
        """
        Convert raw bytes to base64 string.
        No file write. Stays in memory only.
        """
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        # image_bytes is now the only reference; caller should del it
        return b64

    def parse_response(self, raw_text: str) -> ScreenState:
        """
        Deterministically parse the vision model's structured response
        into a ScreenState. Computes confidence score without ML.
        """
        lines = raw_text.strip().splitlines()
        fields: dict[str, str] = {}
        for line in lines:
            if ":" in line:
                key, _, val = line.partition(":")
                fields[key.strip().upper()] = val.strip()

        application = fields.get("APPLICATION", "Unknown")
        activity_raw = fields.get("ACTIVITY", "Unknown")
        text_visible  = fields.get("TEXT_VISIBLE", "no").lower() == "yes"
        summary       = fields.get("SUMMARY", "Screen analysis complete.")
        next_action   = fields.get("NEXT_ACTION", "")

        # Map activity string to enum
        try:
            activity = ScreenActivityType(activity_raw)
        except ValueError:
            activity = ScreenActivityType.UNKNOWN

        # Determine workspace match from application name
        app_lower = application.lower()
        workspace_matched = False
        inferred_activity = activity

        for keyword, (mapped_activity, _workspace) in _APP_MAP.items():
            if keyword in app_lower:
                workspace_matched = True
                if activity == ScreenActivityType.UNKNOWN:
                    inferred_activity = mapped_activity
                break

        # Check if application name is known
        application_detected = application.lower() not in ("unknown", "", "none")

        # Deterministic confidence scoring
        confidence = 0.0
        if application_detected:
            confidence += 40
        if text_visible:
            confidence += 20
        if workspace_matched:
            confidence += 20
        context_coherent = (
            activity != ScreenActivityType.UNKNOWN
            and application_detected
        )
        if context_coherent:
            confidence += 20

        # Use map-based next action if vision didn't provide one
        if not next_action:
            next_action = _NEXT_ACTION_MAP.get(
                inferred_activity, _NEXT_ACTION_MAP[ScreenActivityType.UNKNOWN]
            )

        return ScreenState(
            application=application,
            activity=inferred_activity,
            confidence=min(confidence, 100.0),
            summary=summary,
            next_best_action=next_action,
            timestamp=time.time(),
        )


class CooldownError(Exception):
    """Raised when Boss triggers analysis before the cooldown expires."""
    pass
