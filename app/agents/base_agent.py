from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseAgent(ABC):
    """
    Abstract base class for all autonomous agents in the multi-agent system.
    """
    name: str
    description: str

    @abstractmethod
    def run(self, query: str, context: Optional[dict] = None) -> Any:
        pass
