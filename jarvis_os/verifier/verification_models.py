from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any, Dict

class VerificationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCEL = "cancel"

class VerificationResult(BaseModel):
    status: VerificationStatus
    reason: str
    feedback_data: Optional[Dict[str, Any]] = None

class VerificationInput(BaseModel):
    plan: Dict[str, Any]
    execution_result: Dict[str, Any]
    decision_context: Dict[str, Any]
