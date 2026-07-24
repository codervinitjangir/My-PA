"""
app/core/voice/intent_engine.py — Fast-Path Intent Engine with Confidence Scoring

Evaluates user transcripts to produce structured IntentPredictions.
Executes desktop actions instantly when confidence exceeds threshold (~100ms post-STT).
"""

import re
import logging
from typing import Optional, Dict, Any
from app.core.voice.interfaces import IntentEngine, IntentPrediction

logger = logging.getLogger("J.A.R.V.I.S")

class FastPathIntentEngine(IntentEngine):
    """
    Lightweight, high-accuracy intent engine.
    Uses fast-path pattern matching combined with schema evaluation.
    """

    def __init__(self, brain_service=None):
        self.brain_service = brain_service

    async def classify_intent(self, text: str, context: Optional[Dict[str, Any]] = None) -> IntentPrediction:
        text_clean = text.strip()
        text_lower = text_clean.lower()
        
        # 1. URL pattern
        url_match = re.search(r'(https?://\S+)', text_clean)
        if url_match:
            return IntentPrediction(
                intent_type="action",
                action="open_url",
                target=url_match.group(1),
                confidence=0.98
            )

        # 2. Lock screen / PC
        if any(phrase in text_lower for phrase in ["lock screen", "lock pc", "lock laptop", "lock my screen", "lock the screen"]):
            return IntentPrediction(
                intent_type="action",
                action="lock_screen",
                target="system:lock_screen",
                confidence=0.98
            )

        # 3. Volume control
        vol_match = re.search(r'(?:set volume|volume|sound)\s+(?:to\s+)?(\d{1,3})%?', text_lower)
        if vol_match:
            level = int(vol_match.group(1))
            return IntentPrediction(
                intent_type="action",
                action="volume_set",
                parameters={"level": level},
                confidence=0.95
            )

        if any(w in text_lower for w in ["unmute volume", "unmute sound", "unmute pc", "unmute laptop", "unmute audio"]):
            return IntentPrediction(
                intent_type="action",
                action="volume_unmute",
                confidence=0.95
            )

        if any(w in text_lower for w in ["mute volume", "mute sound", "mute pc", "mute laptop", "mute audio"]):
            return IntentPrediction(
                intent_type="action",
                action="volume_mute",
                confidence=0.95
            )


        # 4. Scroll action
        if "scroll" in text_lower:
            direction = "up" if "up" in text_lower else "down"
            return IntentPrediction(
                intent_type="action",
                action="scroll",
                parameters={"direction": direction, "amount": 500},
                confidence=0.95
            )

        # 5. Screenshot action
        if any(phrase in text_lower for phrase in ["take screenshot", "capture screen", "screen shot", "take a screenshot"]):
            return IntentPrediction(
                intent_type="action",
                action="capture_screen",
                confidence=0.95
            )

        # 6. Open App / Web
        app_match = re.search(r'^(?:open|launch|start|go to)\s+([a-zA-Z0-9\.\s]+)$', text_lower)
        if app_match:
            app_name = app_match.group(1).strip()
            # Ignore conversational words like "open a conversation" or "open your eyes"
            if app_name not in ("up", "your eyes", "conversation", "discussion", "it"):
                return IntentPrediction(
                    intent_type="action",
                    action="open_app",
                    target=app_name,
                    confidence=0.92
                )

        # 7. Play Music / YouTube
        play_match = re.search(r'^(?:play)\s+(.+)$', text_lower)
        if play_match:
            song = play_match.group(1).strip()
            return IntentPrediction(
                intent_type="action",
                action="play",
                target=song,
                confidence=0.92
            )

        # Default fallback to Chat LLM
        return IntentPrediction(
            intent_type="chat",
            action="chat_response",
            target="",
            confidence=0.80
        )
