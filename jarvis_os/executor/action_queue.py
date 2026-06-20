from typing import List, Optional
from jarvis_os.executor.executor_models import Action

class ActionQueue:
    """
    Manages the state and storage of actions awaiting execution.
    States: pending, ready, running, completed, failed, cancelled
    """
    def __init__(self):
        self._actions: List[Action] = []

    def add_action(self, action: Action):
        self._actions.append(action)

    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        for action in self._actions:
            if action.id == action_id:
                return action
        return None

    def get_actions_by_status(self, status: str) -> List[Action]:
        return [a for a in self._actions if a.status == status]

    def update_status(self, action_id: str, new_status: str):
        action = self.get_action_by_id(action_id)
        if action:
            action.status = new_status

    def get_all(self) -> List[Action]:
        return self._actions
