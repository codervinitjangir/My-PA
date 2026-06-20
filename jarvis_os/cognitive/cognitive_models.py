from pydantic import BaseModel
from typing import Dict, Any, Optional
from jarvis_os.verifier.verification_models import VerificationResult

class CognitiveCycleResult(BaseModel):
    goal: str
    identity_state: Optional[Dict[str, Any]] = None
    memory_state: Optional[Dict[str, Any]] = None
    context_state: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    verification: Optional[VerificationResult] = None
