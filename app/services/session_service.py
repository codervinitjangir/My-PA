import json
import logging
from pathlib import Path
from datetime import datetime
from app.services.llm_router import LLMRouter

logger = logging.getLogger("J.A.R.V.I.S")

class SessionService:
    """
    Handles end-of-session summarization (Mark-L Session Memory).
    Generates a 1-2 sentence recap of the day's events to be used in tomorrow's morning briefing.
    """
    def __init__(self, db_path: str = "database/yesterday.json"):
        self.db_path = Path(db_path)
        self.router = LLMRouter()

    def generate_session_summary(self, session_chats: str) -> str:
        """
        Takes raw chat logs from the current session and uses the fast LLM to generate a tight summary.
        """
        if not session_chats or len(session_chats.strip()) < 10:
            return ""

        prompt = f"""
        You are summarizing an AI assistant's session with its user.
        Based on the following conversation logs from today, write exactly ONE or TWO concise sentences summarizing what the user was working on or discussing.
        Write it from the perspective of the AI talking to the user.
        Example: "Yesterday you were working on deploying the backend to Render and fixing memory crashes."
        Example: "Yesterday we discussed Python automation scripts for your emails."

        DO NOT add any other text. Just the 1-2 sentence summary.

        CONVERSATION LOGS:
        {session_chats}
        """

        try:
            # We use the raw Groq fallback provider for speed
            response = self.router.groq_provider.get_response(
                question=prompt,
                chat_history=[],
                use_search=False
            )
            summary = response.strip()
            
            # Save to yesterday.json
            self._save_summary(summary)
            logger.info("[SESSION] Session summary generated successfully.")
            return summary
        except Exception as e:
            logger.error(f"[SESSION] Failed to generate summary: {e}")
            return ""

    def _save_summary(self, summary: str):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": summary,
            "read": False
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def consume_yesterday_summary(self) -> str:
        """Reads yesterday's summary for the morning briefing and marks it as read."""
        if not self.db_path.exists():
            return ""

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not data.get("read", True) and data.get("summary"):
                # Mark as read so it's not repeated
                data["read"] = True
                with open(self.db_path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                    
                return data["summary"]
        except Exception as e:
            logger.warning(f"[SESSION] Failed to consume yesterday summary: {e}")
            
        return ""
