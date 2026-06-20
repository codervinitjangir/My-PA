from datetime import datetime
from jarvis_os.desktop_action.desktop_action_models import ActionRequest, ExecutionResult

class DesktopActionHistory:
    """
    Stores local instance history of actions.
    (Note: The absolute immutable append-only log is handled by SecurityManager).
    """
    def __init__(self):
        self.history = []
        
    def log_action(self, request: ActionRequest, result: ExecutionResult, approved_by_user: bool):
        self.history.append({
            "timestamp": datetime.now(),
            "action": request.action,
            "target": request.target,
            "result": result.message,
            "approved_by_user": approved_by_user
        })
