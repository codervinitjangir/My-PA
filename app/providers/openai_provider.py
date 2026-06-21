from typing import List, Optional, Iterator, Tuple, Any
from app.providers.base_provider import BaseProvider
from app.services.vector_store import VectorStoreService

class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation (Stub ready for integration).
    """
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store_service = vector_store_service
        # TODO: Initialize OpenAI client when API key is available

    def get_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> str:
        return "OpenAI integration coming soon."

    def stream_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> Iterator[Any]:
        yield "OpenAI stream integration coming soon."

    def stream_response_with_prefetched(self, question: str, chat_history: Optional[List[tuple]] = None, formatted_results: Optional[str] = None, payload: Optional[dict] = None, key_start_index: int = 0) -> Iterator[Any]:
        yield "OpenAI prefetched stream integration coming soon."

    def prefetch_web_search(self, question: str, chat_history: Optional[List[tuple]] = None) -> Tuple[str, Optional[dict]]:
        return ("", None)
