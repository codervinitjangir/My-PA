from datetime import datetime
from typing import Dict, Any

class SessionHistory:
    """
    Tracks state mutations within active sessions.
    """
    def __init__(self):
        self.log = []
        
    def record_change(self, action: str, project: str, focus: str, changes: Dict[str, Any]):
        self.log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "project": project,
            "focus": focus,
            "changes": changes
        })
