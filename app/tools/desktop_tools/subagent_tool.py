import logging
import os
import time
from pathlib import Path
import yaml
from app.tools.base_tool import BaseTool
from app.services.automation_service import automation_service
from app.memory.artifact_manager import ArtifactManager

from app.nodes.web_search_node import WebSearchNode
from app.nodes.json_processor_node import JSONProcessorNode
from app.nodes.summary_node import SummaryNode

logger = logging.getLogger("J.A.R.V.I.S")
SKILLS_DIR = Path(os.getcwd()) / "app" / "skills"
artifact_manager = ArtifactManager()

NODE_REGISTRY = {
    "WebSearchNode": WebSearchNode,
    "JSONProcessorNode": JSONProcessorNode,
    "SummaryNode": SummaryNode
}

def _resolve_input(raw_input: str, context: dict) -> str:
    resolved = raw_input
    for step_id, out_data in context.items():
        placeholder = f"{{{{{step_id}.output}}}}"
        if placeholder in resolved:
            resolved = resolved.replace(placeholder, str(out_data))
    return resolved

def _background_skill_execution(skill_name: str, skill_data: dict):
    logger.info(f"[SUBAGENT] Running DAG workflow '{skill_name}' in background...")
    
    context = {}
    steps = skill_data.get("steps", [])
    
    for step in steps:
        step_id = step.get("id")
        node_name = step.get("node")
        raw_input = step.get("input", "")
        
        resolved_input = _resolve_input(raw_input, context)
        
        logger.info(f"[SUBAGENT] Executing Node: {node_name} (Step: {step_id})")
        
        if node_name in NODE_REGISTRY:
            node_instance = NODE_REGISTRY[node_name]()
            try:
                output = node_instance.execute(resolved_input)
                context[step_id] = output
            except Exception as e:
                logger.error(f"[SUBAGENT] Node {node_name} failed: {e}")
                context[step_id] = f"ERROR: {e}"
                break
        else:
            logger.error(f"[SUBAGENT] Unknown node: {node_name}")
            context[step_id] = f"ERROR: Unknown node {node_name}"
            break
            
    final_output = context.get(steps[-1]["id"]) if steps else "No steps executed."
    artifact_manager.upsert(f"workflow_{skill_name}_latest_result", str(final_output))
    logger.info(f"[SUBAGENT] Workflow '{skill_name}' completed. Results dumped to ArtifactManager.")

class SubagentTool(BaseTool):
    name = "execute_skill"
    description = "Executes a multi-step skill defined in a YAML file in the app/skills directory. Supports sequential node-based execution (DAG)."
    
    def execute(self, skill_name: str, run_in_background: bool = False, **kwargs) -> dict:
        logger.info(f"[SUBAGENT] Executing skill: {skill_name} (Background: {run_in_background})")
        
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        
        skill_file = SKILLS_DIR / f"{skill_name}.yaml"
        if not skill_file.exists():
            available = [f.stem for f in SKILLS_DIR.glob("*.yaml")]
            return {"status": "error", "message": f"Skill '{skill_name}' not found. Available skills: {available}"}
            
        try:
            with open(skill_file, "r") as f:
                skill_data = yaml.safe_load(f)
                
            if run_in_background:
                automation_service.run_in_background(_background_skill_execution, skill_name, skill_data)
                return {
                    "status": "success", 
                    "message": f"Workflow '{skill_name}' dispatched to background thread."
                }
            else:
                _background_skill_execution(skill_name, skill_data)
                return {
                    "status": "success", 
                    "message": f"Skill '{skill_name}' completed successfully via DAG nodes.",
                    "skill_definition": skill_data
                }
        except Exception as e:
            logger.error(f"[SUBAGENT] Failed to load skill: {e}")
            return {"status": "error", "message": str(e)}
