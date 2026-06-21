from abc import ABC, abstractmethod
from typing import List, Optional, Iterator, Tuple, Any

class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Ensures that any new provider (OpenAI, Gemini, Local) implements the required interface
    currently expected by ChatService and BrainService.
    """
    
    @abstractmethod
    def get_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> str:
        pass

    @abstractmethod
    def stream_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> Iterator[Any]:
        pass

    @abstractmethod
    def stream_response_with_prefetched(self, question: str, chat_history: Optional[List[tuple]] = None, formatted_results: Optional[str] = None, payload: Optional[dict] = None, key_start_index: int = 0) -> Iterator[Any]:
        pass

    @abstractmethod
    def prefetch_web_search(self, question: str, chat_history: Optional[List[tuple]] = None) -> Tuple[str, Optional[dict]]:
        pass
