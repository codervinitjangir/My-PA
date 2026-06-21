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
        category, task_types, method, elapsed_ms = self.brain.classify(message, chat_history)
        
        # Example of how an orchestrator could intercept specific types:
        # if category == "realtime" and "deep research" in message.lower():
        #     result = self.agents["research_agent"].run(message, {"chat_history": chat_history})
        #     return {"intercepted": True, "result": result}
        
        return {
            "intercepted": False,
            "category": category,
            "task_types": task_types,
            "method": method,
            "elapsed_ms": elapsed_ms
        }
