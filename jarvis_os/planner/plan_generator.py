from typing import List
from jarvis_os.planner.planner_models import Task, Plan, Goal

class PlanGenerator:
    """
    Converts a list of tasks into an ordered, sequential Plan.
    Deterministic, no AI used.
    """
    def generate_plan(self, goal: Goal, tasks: List[Task]) -> Plan:
        # In a deterministic rule-based system, we just execute sequentially.
        # We simulate dependencies by making task N dependent on task N-1.
        
        ordered_tasks = []
        previous_task_id = None
        
        for task in tasks:
            if previous_task_id:
                task.dependencies.append(previous_task_id)
            ordered_tasks.append(task)
            previous_task_id = task.id
            
        return Plan(
            title=f"Plan for: {goal.title}",
            description=f"Generated deterministic sequential plan with {len(tasks)} steps.",
            ordered_tasks=ordered_tasks
        )
