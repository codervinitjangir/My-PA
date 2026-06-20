from jarvis_os.context.context_manager import ContextManager
from jarvis_os.integration.identity_adapter import IdentityAdapter
from jarvis_os.integration.memory_adapter import MemoryAdapter

class ContextAdapter:
    """
    Adapter bridging the Context Engine to the Integration Layer.
    """
    def __init__(self, context_manager: ContextManager, identity_adapter: IdentityAdapter, memory_adapter: MemoryAdapter):
        self.manager = context_manager
        self.identity_adapter = identity_adapter
        self.memory_adapter = memory_adapter

    def build_jarvis_state(self, session_context: dict = None) -> dict:
        """
        Creates the Unified Jarvis State.
        """
        # We can either use the context manager directly or use our adapters
        # Here we construct the precise output requested for the state.
        
        identity_core = self.identity_adapter.get_core_identity()
        selected_memories = self.memory_adapter.get_selected_memories()
        
        # Get dynamic focus from Context Manager
        full_context = self.manager.get_awareness_context(session_context)
        
        return {
            "identity": identity_core,
            "active_projects": identity_core.get("active_projects", []),
            "active_goals": identity_core.get("active_goals", []),
            "current_focus": full_context.get("current_focus", "general"),
            "important_memories": selected_memories,
            "preferences": identity_core.get("preferences", {}),
            "session_context": session_context or {},
            "priority_items": full_context.get("priority_items", [])
        }
