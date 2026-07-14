import logging
from typing import Dict, Any, Optional
from app.services.brain_service import BrainService
from app.agents.base_agent import BaseAgent

logger = logging.getLogger("J.A.R.V.I.S")

class Orchestrator:
    """
    Multi-agent orchestrator. Uses BrainService to classify intent,
    then routes to specialized agents for complex tasks.
    Maintains backward compatibility by returning routing information that ChatService expects.
    """
    def __init__(self, brain_service: BrainService):
        self.brain = brain_service
        self.agents: Dict[str, BaseAgent] = {}
        
    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent
        logger.info(f"[ORCHESTRATOR] Registered agent: {agent.name}")
        
    def route_request(self, message: str, chat_history: Optional[list] = None) -> dict:
        """
        Main entrypoint. Wraps the original brain classify logic.
        Future implementations will intercept complex intents here and route to agents.
        """
        category, task_types, method, elapsed_ms, intent_dict = self.brain.classify(message, chat_history)
        
        # Intercept deep research requests
        if category == "realtime" and any(k in message.lower() for k in ["deep research", "comprehensive research", "deep dive"]):
            if "research_agent" in self.agents:
                try:
                    logger.info("[ORCHESTRATOR] Routing to DeepResearchAgent")
                    result = self.agents["research_agent"].run(message, {"chat_history": chat_history})
                    return {
                        "intercepted": True,
                        "result": result,
                        "category": category,
                        "task_types": task_types,
                        "method": method,
                        "elapsed_ms": elapsed_ms,
                        "intent_dict": intent_dict
                    }
                except Exception as e:
                    logger.error(f"[ORCHESTRATOR] DeepResearchAgent failed: {e}")
        
        return {
            "intercepted": False,
            "category": category,
            "task_types": task_types,
            "method": method,
            "elapsed_ms": elapsed_ms,
            "intent_dict": intent_dict
        }
