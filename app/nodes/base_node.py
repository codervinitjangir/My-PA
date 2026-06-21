from abc import ABC, abstractmethod

class BaseNode(ABC):
    @abstractmethod
    def execute(self, input_data: str) -> str:
        pass
