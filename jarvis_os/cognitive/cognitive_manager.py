from jarvis_os.cognitive.cognitive_pipeline import CognitivePipeline
from jarvis_os.cognitive.cognitive_models import CognitiveCycleResult

class CognitiveManager:
    """
    Entry point for the Cognitive Pipeline.
    Manages the overall thinking loop of Jarvis OS.
    """
    def __init__(self):
        self.pipeline = CognitivePipeline()
        
    def run_cognitive_cycle(self, goal: str) -> dict:
        """
        Runs a complete cognitive cycle for a given user goal.
        Returns the output of the cycle as a dictionary containing:
        - decision
        - plan
        - execution
        - verification
        """
        result: CognitiveCycleResult = self.pipeline.run_cycle_simulation(goal)
        
        # Format the output as requested by Step 6:
        # Output: { decision, plan, execution, verification }
        return {
            "decision": result.decision,
            "plan": result.plan,
            "execution": result.execution,
            "verification": result.verification.dict() if result.verification else None
        }
