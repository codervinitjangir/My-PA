import random
import logging
import requests
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class JokePlugin(BaseTool):
    name = "tell_joke"
    description = "Tells a random programming or general joke."
    
    def execute(self, **kwargs) -> dict:
        try:
            # Using official joke API
            resp = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                joke = f"{data['setup']} ... {data['punchline']}"
                logger.info("[PLUGIN] Fetched a joke.")
                return {"status": "success", "joke": joke}
        except Exception as e:
            logger.warning(f"[PLUGIN] Failed to fetch joke from API: {e}")
            
        # Fallback jokes
        fallback_jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I'd tell you a joke about UDP, but you might not get it.",
            "There are 10 types of people in the world: those who understand binary, and those who don't."
        ]
        return {"status": "success", "joke": random.choice(fallback_jokes)}
