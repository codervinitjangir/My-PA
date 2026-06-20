from pydantic import BaseModel
from typing import Optional

class ActionRequest(BaseModel):
    action: str
    target: str

class ExecutionResult(BaseModel):
    success: bool
    message: str
