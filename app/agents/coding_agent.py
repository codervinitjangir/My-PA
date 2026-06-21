import logging
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.providers.provider_manager import ProviderManager

logger = logging.getLogger("J.A.R.V.I.S")

class CodingAgent(BaseAgent):
    name = "coding_agent"
    description = "Writes, reviews, and refactors code."
    
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        
    def run(self, query: str, context: Optional[dict] = None) -> str:
        logger.info(f"[CODING AGENT] Processing code request: {query}")
        provider = self.provider_manager.get_provider()
        
        # In the future, this can invoke tools like a local syntax checker or execute code securely.
        # For now, we apply a coding-specific persona.
        coding_prompt = f"You are an expert Principal Software Engineer. Write clean, modular, and well-documented code.\n\nRequest: {query}"
        return provider.get_response(coding_prompt, use_search=False)
