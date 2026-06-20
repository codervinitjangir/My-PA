from typing import List
from jarvis_os.memory.memory_models import MemoryItem

class MemoryStore:
    def __init__(self):
        # Placeholder for eventual connection to FAISS or a Graph DB
        self._items: List[MemoryItem] = []
        
    def add(self, item: MemoryItem):
        self._items.append(item)
        
    def get_all(self) -> List[MemoryItem]:
        return self._items
