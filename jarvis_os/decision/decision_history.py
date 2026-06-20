from typing import List, Dict, Any
from jarvis_os.decision.decision_models import Decision, DecisionResult

class DecisionHistory:
    """
    Stores past decisions and their results to eventually train Jarvis behavior.
    """
    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def log_decision(self, decision: Decision):
        self.history.append({
            "decision_id": decision.id,
            "decision": decision.model_dump(),
            "reason": decision.reason,
            "timestamp": decision.created_at,
            "result": None
        })

    def log_result(self, result: DecisionResult):
        for record in self.history:
            if record["decision_id"] == result.decision_id:
                record["result"] = result.model_dump()
                break
                
    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
