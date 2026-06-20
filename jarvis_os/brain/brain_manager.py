from jarvis_os.identity.identity_manager import IdentityManager
from jarvis_os.memory.memory_manager import MemoryManager
from jarvis_os.brain.brain_context_builder import BrainContextBuilder
from jarvis_os.brain.brain_prioritizer import BrainPrioritizer

class BrainManager:
    """
    The orchestrator for the Brain layer.
    Observes, understands, prioritizes, and prepares context.
    """
    def __init__(self):
        self.identity_manager = IdentityManager()
        self.memory_manager = MemoryManager()
        self.context_builder = BrainContextBuilder(self.identity_manager, self.memory_manager)
        self.prioritizer = BrainPrioritizer()

    def prepare_context(self, session_data: dict = None) -> dict:
        return self.context_builder.build_brain_context(session_data)
