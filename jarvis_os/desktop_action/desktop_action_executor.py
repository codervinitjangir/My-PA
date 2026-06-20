from jarvis_os.desktop_action.os_adapter import OSAdapter
from jarvis_os.desktop_action.desktop_action_models import ActionRequest, ExecutionResult

class DesktopActionExecutor:
    """
    Executes validated and approved actions.
    Dry run (simulate=True) is the default.
    """
    def __init__(self):
        self.os_adapter = OSAdapter()
        
    def execute(self, request: ActionRequest, simulate: bool = True) -> ExecutionResult:
        if simulate:
            return ExecutionResult(
                success=True,
                message=f"[SIMULATION] Would execute: {request.action} on {request.target}"
            )
            
        success = self.os_adapter.execute(request.target)
        if success:
            return ExecutionResult(success=True, message=f"Executed {request.action} successfully.")
        else:
            return ExecutionResult(success=False, message=f"Failed to execute {request.action}.")
