from typing import Dict
from app.providers.base_provider import BaseProvider
from app.providers.groq_provider import GroqProvider
from app.services.vector_store import VectorStoreService

class ProviderManager:
    """
    Manages LLM providers to decouple the core application from specific models.
    """
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store = vector_store_service
        self.providers: Dict[str, BaseProvider] = {}
        
        # Initialize default provider
        self.providers["groq"] = GroqProvider(vector_store_service)
        self.default_provider = "groq"

    def get_provider(self, name: str = None) -> BaseProvider:
        target = name or self.default_provider
        if target not in self.providers:
            raise ValueError(f"Provider {target} not configured.")
        return self.providers[target]
