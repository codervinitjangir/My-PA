from datetime import datetime, timedelta
from typing import List
from jarvis_os.memory.memory_models import MemoryItem

class ContextFilter:
    """
    Filters context to prevent overload. Handles expiration and relevance.
    """
    def filter_context(self, items: List[MemoryItem]) -> List[MemoryItem]:
        valid_items = []
        for item in items:
            if not self._is_expired(item):
                valid_items.append(item)
        
        # Prevent overload by capping the list size (e.g., top 10 relevant items)
        return valid_items[:10]

    def _is_expired(self, item: MemoryItem) -> bool:
        content = item.content.lower()
        now = datetime.utcnow()
        
        # Simple heuristic rules for expiration (without AI)
        if "tomorrow" in content or "interview" in content:
            # Expires after 48 hours for a "tomorrow" event
            item_time = datetime.fromisoformat(item.timestamp)
            if now > item_time + timedelta(hours=48):
                return True
                
        if "coding session" in content:
            # Expires after a few hours
            item_time = datetime.fromisoformat(item.timestamp)
            if now > item_time + timedelta(hours=4):
                return True
                
        if "favorite" in content:
            # Never expires
            return False
            
        return False
