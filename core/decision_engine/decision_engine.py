import logging

logger = logging.getLogger("J.A.R.V.I.S")

class DecisionEngine:
    """
    Evaluates context/memory to determine the best action path before tools are executed.
    """
    def __init__(self):
        pass

    def evaluate(self, enriched_query: str) -> str:
        """
        Returns one of:
        - "SILENT": Execution should happen, but without TTS.
        - "TOOL": A tool should be executed.
        - "RESPONSE": Standard conversational response.
        
        V1 Logic:
        If the query context implies a meeting or locked state, return SILENT.
        Otherwise, let the legacy router handle it (returns RESPONSE).
        """
        # A simple string check for V1. In future, this will use LLM/rules.
        if "Meeting: Active" in enriched_query or "PC: Locked" in enriched_query:
            logger.info("[DecisionEngine] Context dictates SILENT mode.")
            return "SILENT"
            
        logger.info("[DecisionEngine] Context dictates normal RESPONSE mode.")
        return "RESPONSE"
