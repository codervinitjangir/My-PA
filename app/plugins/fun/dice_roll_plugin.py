import random
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class DiceRollPlugin(BaseTool):
    name = "dice_roll"
    description = "Rolls a 6-sided die and returns the result."
    
    def execute(self, **kwargs) -> dict:
        result = random.randint(1, 6)
        logger.info(f"[PLUGIN] Dice Roll: {result}")
        return {"status": "success", "result": result}
