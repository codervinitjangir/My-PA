from jarvis_os.planner.planner_models import Plan
from jarvis_os.executor.action_queue import ActionQueue
from jarvis_os.executor.action_dispatcher import ActionDispatcher
from jarvis_os.executor.action_scheduler import ActionScheduler
from jarvis_os.executor.execution_tracker import ExecutionTracker

class ExecutorManager:
    """
    Orchestrates the Executor Foundation.
    Takes a Plan, breaks it into Actions, and manages their scheduling and tracking.
    """
    def __init__(self):
        self.queue = ActionQueue()
        self.dispatcher = ActionDispatcher()
        self.scheduler = ActionScheduler(self.queue)
        self.tracker = ExecutionTracker()

    def submit_plan(self, plan: Plan):
        """Converts a plan into actions and adds them to the queue."""
        actions = self.dispatcher.dispatch_plan(plan)
        for action in actions:
            self.queue.add_action(action)
            
    def get_next_runnable_action(self):
        """Returns the next action that should be executed."""
        action = self.scheduler.get_next_action()
        if action:
            self.queue.update_status(action.id, "ready")
        return action
