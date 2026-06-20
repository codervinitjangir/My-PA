from typing import List, Dict
from jarvis_os.tests.test_results import TestResult

class TestScenarios:
    def __init__(self):
        self.scenarios = [
            {
                "name": "Scenario 1: Daily Plan",
                "input": "What should I do today?",
                "expected_modules": ["awareness", "session", "recommendation", "operator"]
            },
            {
                "name": "Scenario 2: Resume Work",
                "input": "Continue working on Jarvis",
                "expected_modules": ["session", "planner", "recommendation"]
            },
            {
                "name": "Scenario 3: Task Check",
                "input": "What is pending?",
                "expected_modules": ["session", "planner"]
            },
            {
                "name": "Scenario 4: Desktop Execution",
                "input": "Open VS Code",
                "expected_modules": ["desktop_action", "security"]
            },
            {
                "name": "Scenario 5: Active Projects",
                "input": "What projects are active?",
                "expected_modules": ["identity", "awareness"]
            }
        ]
        
    def get_scenarios(self) -> List[Dict]:
        return self.scenarios
