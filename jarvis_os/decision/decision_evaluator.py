from typing import List
from jarvis_os.decision.decision_models import DecisionContext, DecisionCandidate
from jarvis_os.decision.decision_rules import DecisionRules

class DecisionEvaluator:
    """
    Evaluates context to generate possible decisions based on rules.
    """
    def __init__(self):
        self.rules = DecisionRules()

    def evaluate(self, context: DecisionContext) -> List[DecisionCandidate]:
        """
        Takes the current state of the system and evaluates what could happen next.
        """
        candidates = self.rules.apply_rules(context)
        return candidates
