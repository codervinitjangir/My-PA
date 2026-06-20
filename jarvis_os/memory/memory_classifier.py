from jarvis_os.shared.enums import ImportanceLevel
import re

class MemoryClassifier:
    """
    Rules-based classifier to determine the importance of a memory item.
    """
    
    CRITICAL_KEYWORDS = ["emergency", "password", "medical", "urgent", "critical"]
    HIGH_KEYWORDS = ["interview", "tomorrow", "deadline", "meeting", "important", "must"]
    LOW_KEYWORDS = ["favorite", "like", "color", "movie", "song", "prefer"]

    def classify_importance(self, content: str) -> ImportanceLevel:
        content_lower = content.lower()
        
        # Check critical first
        if any(keyword in content_lower for keyword in self.CRITICAL_KEYWORDS):
            return ImportanceLevel.CRITICAL
            
        # Check high
        if any(keyword in content_lower for keyword in self.HIGH_KEYWORDS):
            return ImportanceLevel.HIGH
            
        # Check low
        if any(keyword in content_lower for keyword in self.LOW_KEYWORDS):
            return ImportanceLevel.LOW
            
        # Default fallback
        return ImportanceLevel.MEDIUM
