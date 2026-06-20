from typing import List
from jarvis_os.memory.memory_models import MemoryItem
from jarvis_os.memory.memory_store import MemoryStore
from jarvis_os.memory.memory_retriever import MemoryRetriever
from jarvis_os.memory.memory_classifier import MemoryClassifier
from jarvis_os.shared.enums import MemoryCategory
import uuid
import datetime

class MemoryManager:
    def __init__(self):
        self.store = MemoryStore()
        self.retriever = MemoryRetriever(self.store)
        self.classifier = MemoryClassifier()

    def add_memory(self, content: str, category: MemoryCategory, source: str = "user", tags: List[str] = None):
        importance = self.classifier.classify_importance(content)
        
        item = MemoryItem(
            id=str(uuid.uuid4()),
            category=category,
            importance=importance,
            content=content,
            tags=tags or [],
            source=source
        )
        self.store.add(item)
        return item

    def get_recent_memories(self, limit: int = 5) -> List[dict]:
        memories = self.retriever.retrieve_recent(limit)
        return [m.model_dump() for m in memories]
