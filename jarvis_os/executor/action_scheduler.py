from typing import List, Optional
from jarvis_os.executor.action_queue import ActionQueue
from jarvis_os.executor.executor_models import Action

class ActionScheduler:
    """
    Determines execution order from the ActionQueue.
    Rules: dependencies first, priority second, FIFO third.
    """
    def __init__(self, queue: ActionQueue):
        self.queue = queue

    def _priority_value(self, priority: str) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(priority.lower(), 2)

    def get_next_action(self) -> Optional[Action]:
        """
        Calculates which action should be executed next.
        """
        pending_actions = self.queue.get_actions_by_status("pending")
        if not pending_actions:
            return None

        completed_ids = [a.id for a in self.queue.get_actions_by_status("completed")]

        # Filter actions whose dependencies are fully met
        ready_actions = []
        for action in pending_actions:
            can_run = all(dep in completed_ids for dep in action.dependencies)
            if can_run:
                ready_actions.append(action)

        if not ready_actions:
            return None

        # Sort by priority (highest first), then by creation time (FIFO)
        ready_actions = sorted(
            ready_actions, 
            key=lambda a: (self._priority_value(a.priority), -float(a.created_at.replace('-', '').replace(':', '').replace('T', '').replace('.', ''))),
            reverse=True
        )

        return ready_actions[0]
