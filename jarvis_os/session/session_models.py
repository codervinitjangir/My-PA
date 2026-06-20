from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class WorkSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    domain: str
    project: str
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: SessionStatus = SessionStatus.ACTIVE
    focus: str
    pending_items: List[str] = Field(default_factory=list)
    completed_items: List[str] = Field(default_factory=list)
    notes: str = ""
    priority: int = 1
