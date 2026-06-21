import random
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class CoinFlipPlugin(BaseTool):
    name = "coin_flip"
    description = "Flips a coin and returns heads or tails."
    
    def execute(self, **kwargs) -> dict:
        result = random.choice(["Heads", "Tails"])
        logger.info(f"[PLUGIN] Coin Flip: {result}")
        return {"status": "success", "result": result}
