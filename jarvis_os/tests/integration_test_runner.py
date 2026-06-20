import time
from typing import List
from jarvis_os.tests.test_scenarios import TestScenarios
from jarvis_os.tests.test_results import TestResult, SystemHealth
from jarvis_os.operator.operator_router import OperatorRouter
from jarvis_os.operator.operator_registry import OperatorRegistry

class IntegrationTestRunner:
    """
    Validates routing and integration pipelines. Does NOT execute real actions.
    """
    def __init__(self):
        self.scenarios = TestScenarios()
        self.router = OperatorRouter()
        self.registry = OperatorRegistry()
        
    def run_tests(self) -> List[TestResult]:
        results = []
        for scenario in self.scenarios.get_scenarios():
            start_time = time.time()
            
            # Use OperatorRouter to simulate routing
            route_plan = self.router.route_intent(scenario["input"])
            
            # Add operator explicitly if it orchestrated
            actual_modules = route_plan.target_modules.copy()
            if "generate_suggestions" in route_plan.intent:
                actual_modules.append("operator")
            
            end_time = time.time()
            latency = int((end_time - start_time) * 1000)
            
            # Simple check to see if expected modules are at least hit
            success = any(m in actual_modules for m in scenario["expected_modules"])
            
            results.append(TestResult(
                scenario_name=scenario["name"],
                expected_modules=scenario["expected_modules"],
                routed_modules=actual_modules,
                success=success,
                latency_ms=latency
            ))
            
        return results
        
    def build_system_health(self) -> SystemHealth:
        """
        Hardcoded QA analysis based on architecture mapping.
        """
        registry_health = self.registry.get_health()
        available = registry_health["available_modules"]
        
        # QA Analysis
        # Identity, Memory, Context, Brain, Verifier, Executor are currently bypassed by Operator.
        unused = ["context", "brain", "executor", "verifier"]
        
        # Decision vs Planner overlap
        missing_connections = ["decision -> planner (no direct bridge)", "runtime -> memory (loose coupling)"]
        
        return SystemHealth(
            healthy_modules=[m for m in available if m not in unused],
            degraded_modules=["planner", "memory"],  # Degraded because they aren't fully integrated into Operator yet.
            unused_modules=unused,
            missing_connections=missing_connections
        )
