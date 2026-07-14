import os
from pathlib import Path
from app.tools.base_tool import BaseTool
from app.tools.registry import ToolRegistry
import logging

logger = logging.getLogger("J.A.R.V.I.S")

class CommitSkillTool(BaseTool):
    name = "commit_skill"
    description = "Commits a pending skill to disk and hot-loads it into the active session. ONLY call this AFTER the user has explicitly approved the code."
    
    def execute(self, **kwargs) -> str:
        tool_name = kwargs.get("tool_name")
        if not tool_name:
            return "Error: Missing tool_name."
            
        if tool_name not in ToolRegistry._pending_skills:
            return f"Error: No pending skill found with name '{tool_name}'. Did you call propose_skill first?"
            
        code = ToolRegistry._pending_skills[tool_name]
        
        # Write to disk
        custom_dir = Path(__file__).parent / "custom"
        custom_dir.mkdir(exist_ok=True)
        
        file_path = custom_dir / f"{tool_name}.py"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
                
            # Hot-load it
            ToolRegistry.load_tool_from_file(str(file_path))
            
            # Clean up pending
            del ToolRegistry._pending_skills[tool_name]
            
            return f"Success! Skill '{tool_name}' has been written to {file_path} and hot-loaded into the active session. You can now use it immediately."
        except Exception as e:
            return f"Error committing skill: {str(e)}"
