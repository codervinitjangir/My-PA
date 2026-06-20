from jarvis_os.context.context_builder import ContextBuilder
from jarvis_os.context.context_prioritizer import ContextPrioritizer
from jarvis_os.context.context_filter import ContextFilter
from jarvis_os.context.context_observer import ContextObserver
from jarvis_os.identity.identity_manager import IdentityManager
from jarvis_os.memory.memory_manager import MemoryManager

class ContextManager:
    """
    The orchestrator for the Context Engine.
    Serves as the awareness layer.
    """
    def __init__(self):
        self.identity_manager = IdentityManager()
        self.memory_manager = MemoryManager()
        self.builder = ContextBuilder()
        self.prioritizer = ContextPrioritizer()
        self.filter = ContextFilter()
        self.observer = ContextObserver()

    def get_awareness_context(self, session_data: dict = None) -> dict:
        """
        Compiles what the boss is doing and what matters now.
        """
        identity_data = self.identity_manager.get_identity_context()
        raw_memories = self.memory_manager.store.get_all() # In future, pull relevant based on query
        
        # Filter memories to prevent overload
        filtered_memories = self.filter.filter_context(raw_memories)
        
        # Prioritize what's left
        priority_memories = self.prioritizer.prioritize(filtered_memories)
        
        # Extract items
        projects = identity_data.get("projects", [])
        goals = identity_data.get("goals", {}).get("active_goals", [])
        devices = identity_data.get("devices", [])
        
        return self.builder.build_current_context(
            identity=identity_data,
            projects=projects,
            goals=goals,
            memories=[m.model_dump() for m in filtered_memories],
            devices=devices,
            session=session_data or {},
            priority_items=[m.model_dump() for m in priority_memories]
        )
        
    def notify_event(self, event_type: str, data: any):
        """Hook for external systems to notify the observer."""
        self.observer.observe(event_type, data)
