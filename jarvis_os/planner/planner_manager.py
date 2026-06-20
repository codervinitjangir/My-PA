from jarvis_os.planner.goal_parser import GoalParser
from jarvis_os.planner.task_decomposer import TaskDecomposer
from jarvis_os.planner.plan_generator import PlanGenerator
from jarvis_os.planner.plan_prioritizer import PlanPrioritizer
from jarvis_os.planner.planner_models import Plan

class PlannerManager:
    """
    Orchestrates the process of turning natural language into an executable Plan.
    """
    def __init__(self):
        self.parser = GoalParser()
        self.decomposer = TaskDecomposer()
        self.generator = PlanGenerator()
        self.prioritizer = PlanPrioritizer()

    def create_plan_from_text(self, natural_language_goal: str) -> Plan:
        """
        Full pipeline: Parse -> Decompose -> Generate -> Prioritize.
        """
        # 1. Parse
        goal = self.parser.parse(natural_language_goal)
        
        # 2. Decompose
        tasks = self.decomposer.decompose(goal)
        
        # 3. Generate Plan
        plan = self.generator.generate_plan(goal, tasks)
        
        # 4. Prioritize
        final_plan = self.prioritizer.prioritize(plan)
        
        return final_plan
