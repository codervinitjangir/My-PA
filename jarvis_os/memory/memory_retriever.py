from typing import List
from jarvis_os.memory.memory_store import MemoryStore
from jarvis_os.memory.memory_models import MemoryItem
from jarvis_os.shared.enums import MemoryCategory

class MemoryRetriever:
    def __init__(self, store: MemoryStore):
        self.store = store

    def retrieve_recent(self, limit: int = 5) -> List[MemoryItem]:
        """Retrieve the most recent memories."""
        items = self.store.get_all()
        # Sort by timestamp descending
        items_sorted = sorted(items, key=lambda x: x.timestamp, reverse=True)
        return items_sorted[:limit]

    def retrieve_by_category(self, category: MemoryCategory) -> List[MemoryItem]:
        """Retrieve memories filtered by category."""
        return [item for item in self.store.get_all() if item.category == category]
