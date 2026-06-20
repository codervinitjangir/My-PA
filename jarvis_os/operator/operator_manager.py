from typing import Dict, Any
from jarvis_os.operator.operator_registry import OperatorRegistry
from jarvis_os.operator.operator_router import OperatorRouter
from jarvis_os.operator.operator_summary import OperatorSummary
from jarvis_os.operator.operator_models import OperatorHealth, RoutePlan

class OperatorManager:
    """
    The orchestrator of JARVIS OS. Routes commands to required modules.
    Does NOT act as an autonomous agent.
    """
    def __init__(self):
        self.registry = OperatorRegistry()
        self.router = OperatorRouter()
        self.summary_builder = OperatorSummary()
        
    def get_operator_health(self) -> OperatorHealth:
        health_data = self.registry.get_health()
        return OperatorHealth(**health_data)
        
    def orchestrate(self, user_input: str) -> RoutePlan:
        return self.router.route_intent(user_input)
        
    def build_operator_summary(self, global_state: Dict[str, Any]) -> str:
        return self.summary_builder.build_operator_summary(global_state)
