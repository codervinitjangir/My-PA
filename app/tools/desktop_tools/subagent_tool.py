import logging
import os
import time
from pathlib import Path
import yaml
from app.tools.base_tool import BaseTool
from app.services.automation_service import automation_service
from app.memory.artifact_manager import ArtifactManager

logger = logging.getLogger("J.A.R.V.I.S")
SKILLS_DIR = Path(os.getcwd()) / "app" / "skills"
artifact_manager = ArtifactManager()

def _background_skill_execution(skill_name: str, skill_data: dict):
    """Simulates background execution of a workflow."""
    logger.info(f"[SUBAGENT] Running workflow '{skill_name}' in background...")
    time.sleep(2) # Simulate work
    
    # Save output to artifact
    result = f"Background execution of {skill_name} completed successfully."
    artifact_manager.upsert(f"workflow_{skill_name}_latest_result", result)
    logger.info(f"[SUBAGENT] Workflow '{skill_name}' completed. Results dumped to ArtifactManager.")

class SubagentTool(BaseTool):
    name = "execute_skill"
    description = "Executes a multi-step skill defined in a YAML file in the app/skills directory. Set run_in_background to true to detach long-running workflows."
    
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
                    "message": f"Workflow '{skill_name}' dispatched to background thread. You will not wait for it. Results will be saved to Artifacts."
                }
            else:
                return {
                    "status": "success", 
                    "message": f"Skill loaded successfully. Please follow these steps iteratively:",
                    "skill_definition": skill_data
                }
        except Exception as e:
            logger.error(f"[SUBAGENT] Failed to load skill: {e}")
            return {"status": "error", "message": str(e)}
