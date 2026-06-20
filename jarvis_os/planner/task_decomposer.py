from typing import List
from jarvis_os.planner.planner_models import Goal, Task

class TaskDecomposer:
    """
    Breaks a structured goal into smaller executable tasks.
    Currently rule-based (no AI).
    """
    def decompose(self, goal: Goal) -> List[Task]:
        title_lower = goal.title.lower()
        tasks = []
        
        # Heuristic rules for specific topics
        if "internship" in title_lower or "job" in title_lower:
            tasks = [
                Task(title="Find companies", description="Search for companies offering roles."),
                Task(title="Analyze requirements", description="Extract required skills from job descriptions."),
                Task(title="Compare roles", description="Filter the best matches."),
                Task(title="Prepare resume", description="Tailor the resume to the role."),
                Task(title="Prepare answers", description="Draft answers for common interview questions."),
                Task(title="Submit applications", description="Send applications to the selected companies.")
            ]
        elif "code" in title_lower or "app" in title_lower:
            tasks = [
                Task(title="Define requirements", description="List all required features."),
                Task(title="Setup environment", description="Initialize repository and dependencies."),
                Task(title="Implement core logic", description="Write the main functionality."),
                Task(title="Test", description="Run unit tests to verify."),
            ]
        else:
            # Generic fallback decomposition
            tasks = [
                Task(title="Research", description="Gather information regarding the goal."),
                Task(title="Draft outline", description="Create a basic structure for the work."),
                Task(title="Execute", description="Perform the required actions."),
                Task(title="Review", description="Check the results.")
            ]
            
        return tasks
