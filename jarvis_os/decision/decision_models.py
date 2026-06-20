from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

def _generate_id():
    return str(uuid.uuid4())

def _now():
    return datetime.utcnow().isoformat()

class DecisionCategory(str, Enum):
    ANSWER = "answer"
    REMEMBER = "remember"
    SUGGEST = "suggest"
    PLAN = "plan"
    EXECUTE = "execute"
    WAIT = "wait"
    IGNORE = "ignore"
    ASK = "ask"
    OBSERVE = "observe"

class DecisionContext(BaseModel):
    identity: Dict[str, Any] = {}
    memory: List[Dict[str, Any]] = []
    current_focus: str = "general"
    active_goals: List[str] = []
    priority_items: List[Dict[str, Any]] = []
    planner_output: Optional[Dict[str, Any]] = None

class DecisionCandidate(BaseModel):
    id: str = Field(default_factory=_generate_id)
    category: DecisionCategory
    title: str
    description: str
    priority: str = "medium"
    confidence: float = 1.0
    reason: str
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class Decision(BaseModel):
    id: str = Field(default_factory=_generate_id)
    category: DecisionCategory
    title: str
    description: str
    priority: str
    confidence: float
    reason: str
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class DecisionResult(BaseModel):
    id: str = Field(default_factory=_generate_id)
    decision_id: str
    success: bool
    feedback: str
    created_at: str = Field(default_factory=_now)
