import time
import logging
from datetime import datetime
from app.services.llm_router import LLMRouter

logger = logging.getLogger("J.A.R.V.I.S")

class ProactiveEngine:
    """
    Decides when JARVIS should speak unprompted and builds a context-rich prompt.
    Improvements:
      - Time-of-day awareness
      - Active projects awareness (from IdentityManager)
      - Non-repetitive rotation
    """
    def __init__(self, provider):
        self._rotation = 0
        self.provider = provider

    def generate_proactive_message(self) -> str:
        """
        Builds the context and generates an unprompted message via Groq.
        """
        now = datetime.now()
        hour = now.hour

        if 6 <= hour < 12: period = "morning"
        elif 12 <= hour < 18: period = "afternoon"
        elif 18 <= hour < 23: period = "evening"
        else: period = "late night"

        # Load identity context
        ident_ctx = ""
        try:
            from app.memory.identity_manager import IdentityManager
            ident_ctx = IdentityManager().get_identity_context()
        except:
            pass

        # Rotating context focus
        focus_index = self._rotation % 3
        if focus_index == 0:
            focus = "Focus on the user's active projects or goals. Ask how something is going, or offer a relevant tip."
        elif focus_index == 1:
            focus = f"Focus on the time of day ({period}) and the user's wellbeing. A warm check-in or a reminder to take a break."
        else:
            focus = "Focus on something genuinely interesting or useful — a fact, a suggestion, or a proactive thought."

        self._rotation += 1

        prompt = f"""
        You are JARVIS. The user has been quiet for a while, and you are initiating a proactive check-in.
        
        {ident_ctx}
        
        CURRENT TIME: {now.strftime("%I:%M %p")} ({period})
        
        DIRECTIVE:
        {focus}
        
        RULES:
        - Write exactly ONE or TWO concise sentences.
        - Speak naturally, like a highly capable AI assistant (Iron Man style).
        - DO NOT say "I noticed you've been quiet" or "Since you've been silent".
        - Just confidently state your thought or ask your question.
        - Address the user by their TITLE if appropriate.
        """

        try:
            # Groq is fastest for proactive generation
            resp = self.provider.get_response(
                question=prompt,
                chat_history=[],
                use_search=False
            )
            logger.info("[PROACTIVE] Generated message successfully.")
            return resp.strip()
        except Exception as e:
            logger.error(f"[PROACTIVE] Failed to generate message: {e}")
            return ""
