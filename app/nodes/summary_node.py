from .base_node import BaseNode
import logging
logger = logging.getLogger("J.A.R.V.I.S")

class SummaryNode(BaseNode):
    def execute(self, input_data: str) -> str:
        logger.info("[SummaryNode] Summarizing data...")
        return f"[SUMMARY] {input_data}"
