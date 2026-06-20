import os
import json
from datetime import datetime
from typing import Dict, Any

class SecurityAudit:
    """
    Global immutable audit trail for JARVIS OS.
    Append-only operations. Never overwrites.
    """
    def __init__(self, log_path: str = "security_audit.jsonl"):
        self.log_path = log_path
        
    def log_event(self, request: str, decision: str, approval: str, execution: str, result: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request": request,
            "decision": decision,
            "approval": approval,
            "execution": execution,
            "result": result
        }
        
        # Append only
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
