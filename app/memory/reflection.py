import logging
from app.memory.memory_manager import MemoryManager
from app.providers.provider_manager import ProviderManager

logger = logging.getLogger("J.A.R.V.I.S")

class SelfCorrectionLoop:
    """
    Evaluates past actions to correct mistakes and learn over time.
    """
    def __init__(self, memory_manager: MemoryManager, provider_manager: ProviderManager):
        self.memory = memory_manager
        self.provider = provider_manager
        
    def evaluate_task(self, task_intent: str, outcome: str, user_feedback: str = None) -> bool:
        """
        Analyzes the outcome of a task. If it failed or received negative feedback,
        records a correction in long-term memory.
        """
        if user_feedback and any(word in user_feedback.lower() for word in ["wrong", "not what", "incorrect", "bad"]):
            logger.info("[REFLECTION] Negative feedback detected. Analyzing mistake...")
            prompt = (
                f"Task: {task_intent}\n"
                f"Outcome: {outcome}\n"
                f"Feedback: {user_feedback}\n\n"
                "What went wrong and how should I avoid this in the future? State the lesson clearly."
            )
            
            provider = self.provider.get_provider()
            lesson = provider.get_response(prompt, use_search=False)
            
            self.memory.add_to_long_term(f"LESSON LEARNED: {lesson}", {"type": "reflection"})
            return False
            
        logger.info("[REFLECTION] Task evaluated successfully. No correction needed.")
        return True
