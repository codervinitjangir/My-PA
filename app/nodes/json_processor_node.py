from .base_node import BaseNode
import logging
logger = logging.getLogger("J.A.R.V.I.S")

class JSONProcessorNode(BaseNode):
    def execute(self, input_data: str) -> str:
        logger.info("[JSONProcessorNode] Processing JSON data...")
        return f"{input_data} -> [PROCESSED JSON]"
