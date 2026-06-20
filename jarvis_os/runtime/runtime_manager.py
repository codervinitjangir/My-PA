import logging
from jarvis_os.runtime.runtime_context import RuntimeContext

logger = logging.getLogger("J.A.R.V.I.S")

class RuntimeManager:
    """
    Manages the runtime context extraction for Jarvis OS.
    It builds a lightweight, token-safe context strictly for generative AI consumption.
    """
    def __init__(self):
        self.context = RuntimeContext()
        
    def build_ai_context(self) -> str:
        """
        Builds the compact context (400-500 words max) and logs the state.
        Prioritizes: Current focus, Active goals, Active projects, Top 3 important memories, Current priorities.
        """
        compact_string = self.context.compile_compact_context()
        
        # Word count check
        word_count = len(compact_string.split())
        
        # Logging decision state explicitly per requirements
        logger.info(
            "[JARVIS OS RUNTIME] Context built | Size: %d chars (~%d words)",
            len(compact_string),
            word_count
        )
        logger.info(
            "[JARVIS OS RUNTIME] State - Focus: %s | Active Goals: %d | Decision: Context Injected",
            self.context.state.current_focus,
            len(self.context.state.active_goals)
        )
        
        # Failsafe limit to prevent token bloat
        if word_count > 500:
            logger.warning("[JARVIS OS RUNTIME] Context exceeded 500 words (%d). Truncating.", word_count)
            compact_string = " ".join(compact_string.split()[:500]) + "\n</jarvis_os_context> (Truncated)"
            
        return compact_string
