import logging
import json
import concurrent.futures
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
        
    def _decompose_task(self, task: str, llm_router) -> list:
        prompt = (
            "You are an expert Task Decomposer. Break down the following complex request into 2 to 4 independent sub-tasks "
            "that can be researched or executed in parallel.\n"
            "Output ONLY a valid JSON array of strings, where each string is a self-contained instruction for a sub-agent.\n"
            f"Task: {task}"
        )
        resp = llm_router.get_response(prompt).strip()
        if resp.startswith('```json'): resp = resp[7:-3]
        elif resp.startswith('```'): resp = resp[3:-3]
        
        try:
            return json.loads(resp)
        except:
            return [task] # Fallback to original task if JSON fails

    def _execute_subtask(self, subtask: str, llm_router) -> str:
        prompt = (
            f"You are a specialized sub-agent. Complete the following task to the best of your ability. "
            f"Be detailed and factual.\nTask: {subtask}"
        )
        return llm_router.get_response(prompt)

    def _synthesize_results(self, original_task: str, subtasks: list, results: list, llm_router) -> str:
        combined_context = ""
        for i, (task, res) in enumerate(zip(subtasks, results)):
            combined_context += f"--- Subtask {i+1}: {task} ---\n{res}\n\n"
            
        prompt = (
            "You are the master Synthesizer. You delegated a complex task to multiple sub-agents. "
            "Below are their responses. Synthesize their findings into a single, cohesive, and comprehensive answer "
            "that fully addresses the original user request.\n\n"
            f"Original Request: {original_task}\n\n"
            f"Sub-Agent Findings:\n{combined_context}"
        )
        return llm_router.get_response(prompt)

    def route_request(self, message: str, chat_history: Optional[list] = None, llm_router=None) -> dict:
        """
        Main entrypoint. Wraps the original brain classify logic.
        Future implementations will intercept complex intents here and route to agents.
        """
        category, task_types, method, elapsed_ms, intent_dict = self.brain.classify(message, chat_history)
        
        # Intercept deep reasoning requests using the new Multi-Agent Decomposition
        if intent_dict.get("reasoning_level") == "deep" and llm_router is not None:
            logger.info("[ORCHESTRATOR] Deep reasoning detected. Decomposing task...")
            try:
                subtasks = self._decompose_task(message, llm_router)
                logger.info(f"[ORCHESTRATOR] Decomposed into {len(subtasks)} subtasks: {subtasks}")
                
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(subtasks)) as executor:
                    future_to_task = {executor.submit(self._execute_subtask, task, llm_router): task for task in subtasks}
                    for future in concurrent.futures.as_completed(future_to_task):
                        try:
                            res = future.result()
                            results.append(res)
                        except Exception as e:
                            results.append(f"Error executing subtask: {e}")
                            
                logger.info("[ORCHESTRATOR] Subtasks completed. Synthesizing...")
                final_answer = self._synthesize_results(message, subtasks, results, llm_router)
                
                return {
                    "intercepted": True,
                    "result": final_answer,
                    "category": category,
                    "task_types": task_types,
                    "method": method,
                    "elapsed_ms": elapsed_ms,
                    "intent_dict": intent_dict
                }
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Multi-Agent decomposition failed: {e}")
                # Fall through to standard routing if decomposition fails
        
        # Original legacy interceptor for 'research_agent'
        if category == "realtime" and any(k in message.lower() for k in ["deep research", "comprehensive research", "deep dive"]):
            if "research_agent" in self.agents:
                try:
                    logger.info("[ORCHESTRATOR] Routing to legacy DeepResearchAgent")
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
