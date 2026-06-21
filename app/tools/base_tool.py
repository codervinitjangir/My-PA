from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    """
    Abstract base class for all standalone capabilities (tools) in JARVIS.
    """
    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass
