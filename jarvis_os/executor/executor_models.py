from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import uuid

def _generate_id():
    return str(uuid.uuid4())

def _now():
    return datetime.utcnow().isoformat()

class Action(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str
    status: str = "pending"  # pending, ready, running, completed, failed, cancelled
    priority: str = "medium"
    dependencies: List[str] = []
    payload: Dict[str, Any] = {}
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class ExecutionResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    retries_used: int = 0

class Execution(BaseModel):
    id: str = Field(default_factory=_generate_id)
    action_id: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: float = 0.0
    status: str = "pending"
    errors: List[str] = []
    retries: int = 0
    result: Optional[ExecutionResult] = None

class ActionQueueModel(BaseModel):
    actions: List[Action] = []
