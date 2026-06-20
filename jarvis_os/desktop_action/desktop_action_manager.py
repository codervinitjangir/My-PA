from jarvis_os.desktop_action.desktop_action_models import ActionRequest, ExecutionResult
from jarvis_os.desktop_action.desktop_action_validator import DesktopActionValidator
from jarvis_os.desktop_action.desktop_action_executor import DesktopActionExecutor
from jarvis_os.desktop_action.desktop_action_history import DesktopActionHistory
from jarvis_os.security.security_manager import SecurityManager

class DesktopActionManager:
    """
    The orchestrator. Pipeline: Request -> Validator -> Safety Lock -> Permission -> OS Adapter -> Execute
    """
    def __init__(self):
        self.validator = DesktopActionValidator()
        self.executor = DesktopActionExecutor()
        self.history = DesktopActionHistory()
        self.security = SecurityManager()
        
    def process_request(self, action: str, target: str, user_approved: bool, simulate: bool = True) -> ExecutionResult:
        request = ActionRequest(action=action, target=target)
        
        # 1. Validator & Safety Lock
        is_safe = self.validator.validate(request)
        if not is_safe:
            self.security.log_action(f"{action}:{target}", "REJECT_UNSAFE", "N/A", "NO", "Safety Lock Triggered")
            return ExecutionResult(success=False, message="Rejected by Safety Lock.")
            
        # 2. Permission Layer
        if not user_approved:
            self.security.log_action(f"{action}:{target}", "SAFE", "DENIED", "NO", "User Rejected")
            return ExecutionResult(success=False, message="User denied permission.")
            
        # 3. Execution (OS Adapter via Executor)
        result = self.executor.execute(request, simulate=simulate)
        
        # 4. History and Global Audit
        self.history.log_action(request, result, user_approved)
        exec_status = "SIMULATED" if simulate else "EXECUTED"
        self.security.log_action(f"{action}:{target}", "SAFE", "APPROVED", exec_status, result.message)
        
        return result
