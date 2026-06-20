from datetime import datetime
from jarvis_os.executor.executor_models import Execution, ExecutionResult
import time

class ExecutionTracker:
    """
    Tracks the lifecycle of an execution, including duration and retry logic.
    """
    MAX_RETRIES = 3
    BACKOFF_SCHEDULE = [1, 2, 5]

    def __init__(self):
        self.executions = {}

    def start_execution(self, action_id: str) -> Execution:
        execution = Execution(
            action_id=action_id,
            started_at=datetime.utcnow().isoformat(),
            status="running"
        )
        self.executions[execution.id] = execution
        return execution

    def end_execution(self, execution_id: str, success: bool, output: any = None, error: str = None):
        execution = self.executions.get(execution_id)
        if not execution:
            return
            
        execution.ended_at = datetime.utcnow().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(execution.started_at)
        end = datetime.fromisoformat(execution.ended_at)
        execution.duration_seconds = (end - start).total_seconds()
        
        execution.status = "completed" if success else "failed"
        
        if error:
            execution.errors.append(error)
            
        execution.result = ExecutionResult(
            success=success,
            output=output,
            error=error,
            retries_used=execution.retries
        )

    def calculate_backoff(self, current_retry: int) -> int:
        """Returns the seconds to wait before the next retry."""
        if current_retry >= self.MAX_RETRIES:
            return -1 # Should not retry
        
        if current_retry < len(self.BACKOFF_SCHEDULE):
            return self.BACKOFF_SCHEDULE[current_retry]
        
        return self.BACKOFF_SCHEDULE[-1]
