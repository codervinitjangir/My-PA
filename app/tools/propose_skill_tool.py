from app.tools.base_tool import BaseTool
from app.tools.registry import ToolRegistry
import logging

logger = logging.getLogger("J.A.R.V.I.S")

class ProposeSkillTool(BaseTool):
    name = "propose_skill"
    description = "Proposes a new python tool (skill) to be created. You MUST call this first when creating a new tool. It stores the code as pending. You must then show the code to the user and ask for approval. DO NOT execute this tool if the user hasn't asked for a new capability."
    
    def execute(self, **kwargs) -> str:
        tool_name = kwargs.get("tool_name")
        code = kwargs.get("code")
        
        if not tool_name or not code:
            return "Error: Missing tool_name or code."
            
        ToolRegistry._pending_skills[tool_name] = code
        
        return (f"Successfully staged '{tool_name}' in memory. "
                "CRITICAL NEXT STEP: You MUST now present this code to the user in your chat response "
                "and ask 'Do you approve adding this skill?'. Do NOT call commit_skill until they explicitly say yes.")
