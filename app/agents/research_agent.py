import logging
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.providers.base_provider import BaseProvider

logger = logging.getLogger("J.A.R.V.I.S")

class DeepResearchAgent(BaseAgent):
    name = "research_agent"
    description = "Performs deep web research and synthesizes complex information."
    
    def __init__(self, provider: BaseProvider):
        self.provider = provider
        
    def run(self, query: str, context: Optional[dict] = None) -> str:
        logger.info(f"[RESEARCH AGENT] Starting deep research on: {query}")
        provider = self.provider
        
        # Deep research pattern: prefetch web results then synthesize a comprehensive answer
        formatted_results, payload = provider.prefetch_web_search(query, context.get("chat_history", []) if context else [])
        
        if formatted_results:
            logger.info("[RESEARCH AGENT] Synthesizing results...")
            synthesis_prompt = f"Based on the following deep research results:\n{formatted_results}\n\nProvide a comprehensive, highly detailed answer to: {query}"
            return provider.get_response(synthesis_prompt, use_search=False)
            
        logger.warning("[RESEARCH AGENT] No search results found, falling back to general LLM knowledge.")
        return provider.get_response(query, use_search=True)
