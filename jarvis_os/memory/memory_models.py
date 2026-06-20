from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from jarvis_os.shared.enums import MemoryCategory, ImportanceLevel

class MemoryItem(BaseModel):
    id: str
    category: MemoryCategory
    importance: ImportanceLevel
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    content: str
    tags: List[str] = []
    source: str
