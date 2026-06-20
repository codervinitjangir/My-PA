from typing import Dict, Any, List
from jarvis_os.memory.memory_models import MemoryItem

class ContextPrioritizer:
    """
    Scores and prioritizes context elements based on urgency and relevance.
    """
    HIGH_KEYWORDS = ["today", "tomorrow", "active", "deadline", "interview", "coding", "work", "urgent"]
    MEDIUM_KEYWORDS = ["weekly", "study", "ongoing"]
    LOW_KEYWORDS = ["old", "obsolete", "past"]

    def prioritize(self, items: List[MemoryItem]) -> List[MemoryItem]:
        for item in items:
            item.importance = self._score_item(item.content)
        # Sort items by importance: CRITICAL > HIGH > MEDIUM > LOW
        # For simplicity, returning sorted based on string matching
        return sorted(items, key=lambda x: self._importance_value(x.importance), reverse=True)

    def _score_item(self, content: str) -> str:
        content_lower = content.lower()
        if any(kw in content_lower for kw in self.HIGH_KEYWORDS):
            return "high"
        if any(kw in content_lower for kw in self.MEDIUM_KEYWORDS):
            return "medium"
        if any(kw in content_lower for kw in self.LOW_KEYWORDS):
            return "low"
        return "medium"
        
    def _importance_value(self, importance: str) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(importance, 2)
