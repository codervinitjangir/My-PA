from jarvis_os.identity.identity_manager import IdentityManager
from jarvis_os.memory.memory_manager import MemoryManager
from jarvis_os.context.context_manager import ContextManager

from jarvis_os.integration.identity_adapter import IdentityAdapter
from jarvis_os.integration.memory_adapter import MemoryAdapter
from jarvis_os.integration.context_adapter import ContextAdapter
from jarvis_os.integration.brain_adapter import BrainAdapter

class IntegrationManager:
    """
    The orchestrator of the Integration Layer.
    Acts as the bridge between the MVP Jarvis app and Jarvis OS.
    """
    def __init__(self):
        # Initialize core engines
        self.identity_manager = IdentityManager()
        self.memory_manager = MemoryManager()
        self.context_manager = ContextManager()

        # Initialize adapters
        self.identity_adapter = IdentityAdapter(self.identity_manager)
        self.memory_adapter = MemoryAdapter(self.memory_manager)
        self.context_adapter = ContextAdapter(self.context_manager, self.identity_adapter, self.memory_adapter)
        self.brain_adapter = BrainAdapter()

    def build_jarvis_state(self, session_context: dict = None) -> dict:
        """Returns the Unified Jarvis State dictionary."""
        return self.context_adapter.build_jarvis_state(session_context)

    def build_ai_context_string(self, session_context: dict = None) -> str:
        """Returns the concise context string ready to be injected into an LLM prompt."""
        state = self.build_jarvis_state(session_context)
        return self.brain_adapter.build_ai_context(state)
