from typing import Dict, Any
from jarvis_os.verifier.verification_models import VerificationInput, VerificationResult
from jarvis_os.verifier.verification_rules import VerificationRules
from jarvis_os.verifier.verification_history import VerificationHistory

class VerifierManager:
    """
    Orchestrates the Verifier Engine.
    Evaluates whether an execution was successful and what should happen next.
    """
    def __init__(self):
        self.history = VerificationHistory()
        self.rules = VerificationRules()
        
    def verify(self, plan: Dict[str, Any], execution_result: Dict[str, Any], decision_context: Dict[str, Any]) -> VerificationResult:
        """
        Takes the plan, execution result, and decision context,
        and outputs a deterministic VerificationResult.
        """
        verification_input = VerificationInput(
            plan=plan,
            execution_result=execution_result,
            decision_context=decision_context
        )
        
        result = self.rules.apply_rules(verification_input)
        self.history.log_result(result)
        
        return result
