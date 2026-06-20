from typing import List
from jarvis_os.planner.planner_models import Task, Plan
from jarvis_os.executor.executor_models import Action

class ActionDispatcher:
    """
    Receives tasks from the Planner and converts them into executable Actions.
    Does NOT execute them. Only prepares them for the ActionQueue.
    """
    def dispatch_plan(self, plan: Plan) -> List[Action]:
        actions = []
        for task in plan.ordered_tasks:
            action = Action(
                id=task.id, # Keep IDs aligned or map them
                title=f"Execute: {task.title}",
                description=task.description,
                priority=task.priority,
                dependencies=task.dependencies,
                status="pending"
            )
            actions.append(action)
        return actions
