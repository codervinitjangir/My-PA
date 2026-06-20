from jarvis_os.memory.memory_manager import MemoryManager
from typing import List, Dict, Any

class MemoryAdapter:
    """
    Adapter bridging the Memory Engine to the Integration Layer.
    Implements Memory Selection Rules.
    """
    def __init__(self, memory_manager: MemoryManager):
        self.manager = memory_manager

    def get_selected_memories(self) -> List[Dict[str, Any]]:
        """
        Memory Selection Rules:
        Only include high priority, active, relevant, recent.
        Never inject everything.
        """
        all_memories = self.manager.store.get_all()
        selected = []
        for memory in all_memories:
            # Select critical or high priority memories
            if memory.importance in ["critical", "high"]:
                selected.append(memory)
                
        # Sort by timestamp descending and limit to top 5 to keep it concise
        selected = sorted(selected, key=lambda x: x.timestamp, reverse=True)[:5]
        return [m.model_dump() for m in selected]
