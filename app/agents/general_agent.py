import logging
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.providers.provider_manager import ProviderManager

logger = logging.getLogger("J.A.R.V.I.S")

class GeneralAgent(BaseAgent):
    name = "general_agent"
    description = "Handles casual chat, greetings, and generic inquiries."
    
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        
    def run(self, query: str, context: Optional[dict] = None) -> str:
        logger.info(f"[GENERAL AGENT] Processing general chat: {query}")
        provider = self.provider_manager.get_provider()
        return provider.get_response(query, context.get("chat_history", []) if context else [], use_search=False)
