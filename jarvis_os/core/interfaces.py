from abc import ABC, abstractmethod
from typing import Dict, Any

class OperatorInterface(ABC):
    @abstractmethod
    def route_intent(self, intent: str) -> Dict[str, Any]:
        pass

class CapabilityInterface(ABC):
    """
    The universal contract for all JARVIS OS capabilities.
    Any new capability must implement these exactly to be routed by the Operator.
    """
    @abstractmethod
    def initialize(self) -> bool:
        pass
        
    @abstractmethod
    def health(self) -> dict:
        pass
        
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> bool:
        pass
        
    @abstractmethod
    def shutdown(self) -> bool:
        pass

class SecurityInterface(ABC):
    @abstractmethod
    def validate_action(self, action: str, target: str) -> bool:
        pass
