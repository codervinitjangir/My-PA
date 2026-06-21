import logging
import os
from pathlib import Path
import yaml
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

SKILLS_DIR = Path(os.getcwd()) / "app" / "skills"

class SubagentTool(BaseTool):
    name = "execute_skill"
    description = "Executes a multi-step skill defined in a YAML file in the app/skills directory. You can use this to execute complex preset workflows."
    
    def execute(self, skill_name: str, **kwargs) -> dict:
        logger.info(f"[SUBAGENT] Executing skill: {skill_name}")
        
        # Ensure dir exists
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        
        skill_file = SKILLS_DIR / f"{skill_name}.yaml"
        if not skill_file.exists():
            # Let's list available ones
            available = [f.stem for f in SKILLS_DIR.glob("*.yaml")]
            return {"status": "error", "message": f"Skill '{skill_name}' not found. Available skills: {available}"}
            
        try:
            with open(skill_file, "r") as f:
                skill_data = yaml.safe_load(f)
                
            return {
                "status": "success", 
                "message": f"Skill loaded successfully. Please follow these steps iteratively:",
                "skill_definition": skill_data
            }
        except Exception as e:
            logger.error(f"[SUBAGENT] Failed to load skill: {e}")
            return {"status": "error", "message": str(e)}
