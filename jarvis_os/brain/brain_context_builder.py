from jarvis_os.identity.identity_manager import IdentityManager
from jarvis_os.memory.memory_manager import MemoryManager
from jarvis_os.shared.types import ContextDict

class BrainContextBuilder:
    def __init__(self, identity_manager: IdentityManager, memory_manager: MemoryManager):
        self.identity_manager = identity_manager
        self.memory_manager = memory_manager

    def build_brain_context(self, session_context: dict = None) -> ContextDict:
        """
        Builds the unified context dictionary that serves as the Brain's source of truth.
        """
        identity = self.identity_manager.get_identity_context()
        recent_memories = self.memory_manager.get_recent_memories(limit=5)
        
        return {
            "identity": {
                "name": identity.get("name", ""),
            },
            "active_projects": identity.get("projects", []),
            "active_goals": identity.get("goals", {}).get("active_goals", []),
            "recent_memories": recent_memories,
            "preferences": identity.get("preferences", {}),
            "current_session": session_context or {}
        }
