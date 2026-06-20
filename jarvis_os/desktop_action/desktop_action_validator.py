from jarvis_os.desktop_action.safety_lock import SafetyLock
from jarvis_os.desktop_action.desktop_action_models import ActionRequest

class DesktopActionValidator:
    def __init__(self):
        self.safety_lock = SafetyLock()
        
    def validate(self, request: ActionRequest) -> bool:
        return self.safety_lock.check_safety(request.action, request.target)
