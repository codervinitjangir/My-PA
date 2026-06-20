import logging
import time
import json
from jarvis_os.core.global_state import build_global_state
from jarvis_os.operator.operator_router import OperatorRouter

logger = logging.getLogger("J.A.R.V.I.S")

class OperatorRuntime:
    def __init__(self, groq_service):
        self.groq_service = groq_service
        self.router = OperatorRouter()

    def process_user_request(self, session_id: str, message: str) -> str:
        """
        Operator Runtime Execution Flow:
        User Input -> Operator -> Global State -> Capability Router -> GroqService -> Response
        """
        start_time = time.perf_counter()
        logger.info(f"[OPERATOR] Received input | Session: {session_id[:8]} | Message: {message[:50]}")
        
        # 1. Collect global state
        global_state = build_global_state()
        state_str = json.dumps(global_state, indent=2)
        
        # 2. Call capability router
        route_plan = self.router.route_intent(message)
        modules_used = route_plan.target_modules
        logger.info(f"[OPERATOR] Modules used: {modules_used}")
        
        # 3. Build unified context
        context_parts = [
            f"=== OPERATOR GLOBAL STATE ===",
            state_str,
            f"=== CAPABILITY ROUTING ===",
            f"Routed Intent: {route_plan.intent}",
            f"Active Modules: {', '.join(modules_used)}"
        ]
        unified_context = "\n\n".join(context_parts)
        
        context_size = len(unified_context)
        logger.info(f"[OPERATOR] Context size: {context_size} chars")
        
        # 4. Call GroqService (Reasoning Engine)
        try:
            # We bypass the legacy BrainService and use Groq directly as a parsing engine.
            # We inject the unified_context as an extra system part.
            prompt, messages = self.groq_service._build_prompt_and_messages(
                question=message,
                chat_history=None, # In a full implementation, we'd pass session history
                extra_system_parts=[unified_context]
            )
            response = self.groq_service._invoke_llm(prompt, messages, message)
            
            execution_time = time.perf_counter() - start_time
            logger.info(f"[OPERATOR] Execution time: {execution_time:.3f}s")
            
            return response
            
        except Exception as e:
            logger.warning(f"[OPERATOR] Warnings/Error during execution: {str(e)}")
            return "I encountered an error while processing your request through the Operator."
