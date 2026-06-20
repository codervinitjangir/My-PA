import os
import logging

logger = logging.getLogger("J.A.R.V.I.S")

class RequestRouter:
    """
    Dedicated interception layer.
    Checks ENABLE_OPERATOR_RUNTIME flag.
    Routes to legacy pipeline or new Operator Runtime.
    """
    def __init__(self, chat_service, operator_runtime):
        self.chat_service = chat_service
        self.operator_runtime = operator_runtime
        
    def process_request(self, session_id: str, message: str) -> str:
        enable_operator = os.getenv("ENABLE_OPERATOR_RUNTIME", "false").lower() == "true"
        
        if enable_operator:
            logger.info("[ROUTER] Operator Runtime is ENABLED. Routing via Operator.")
            return self.operator_runtime.process_user_request(session_id, message)
        else:
            logger.info("[ROUTER] Operator Runtime is DISABLED. Routing via Legacy ChatService.")
            return self.chat_service.process_message(session_id, message)
            
    def process_request_stream(self, session_id: str, message: str):
        enable_operator = os.getenv("ENABLE_OPERATOR_RUNTIME", "false").lower() == "true"
        
        if enable_operator:
            logger.info("[ROUTER] Operator Runtime is ENABLED. Routing via Operator (Streaming unsupported yet, fallback to sync).")
            # For this sprint, we just yield the sync response if streaming through Operator
            response = self.operator_runtime.process_user_request(session_id, message)
            yield response
        else:
            logger.info("[ROUTER] Operator Runtime is DISABLED. Routing via Legacy ChatService stream.")
            yield from self.chat_service.process_message_stream(session_id, message)
