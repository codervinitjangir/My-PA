from .base_node import BaseNode
import logging
logger = logging.getLogger("J.A.R.V.I.S")

class WebSearchNode(BaseNode):
    def execute(self, input_data: str) -> str:
        logger.info(f"[WebSearchNode] Searching web for: {input_data}")
        # Integration point for AdvancedBrowserTool
        return f"[SEARCH RESULTS FOR: {input_data}] ...mock data..."
