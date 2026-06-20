from typing import Optional
from jarvis_os.decision.decision_models import DecisionContext, Decision
from jarvis_os.decision.decision_evaluator import DecisionEvaluator
from jarvis_os.decision.decision_selector import DecisionSelector
from jarvis_os.decision.decision_history import DecisionHistory

class DecisionManager:
    """
    Orchestrates the Decision Engine.
    Determines WHAT should happen next.
    """
    def __init__(self):
        self.evaluator = DecisionEvaluator()
        self.selector = DecisionSelector()
        self.history = DecisionHistory()

    def decide_next_action(self, context: dict) -> Optional[Decision]:
        """
        Takes the unified Jarvis State dictionary and determines the next decision.
        """
        decision_context = DecisionContext(**context)
        
        # 1. Evaluate Context -> Candidates
        candidates = self.evaluator.evaluate(decision_context)
        
        # 2. Select Best Decision
        decision = self.selector.select(candidates)
        
        # 3. Log History
        if decision:
            self.history.log_decision(decision)
            
        return decision
