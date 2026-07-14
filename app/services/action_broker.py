import logging
import json
from typing import Dict, Any, Tuple

logger = logging.getLogger("J.A.R.V.I.S.Broker")

# List of tools that require explicit user confirmation before executing
IRREVERSIBLE_TOOLS = {
    "send_email",
    "delete_file",
    "create_calendar_event"
}

class ActionBroker:
    """
    Acts as a gateway for tool execution. 
    Classifies tools as reversible or irreversible and pauses execution to ask for confirmation if needed.
    """
    
    @classmethod
    def dispatch(cls, tool_name: str, args: Dict[str, Any], confirmed: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Returns (executed: bool, message: str, pending_action_dict: dict)
        """
        if tool_name in IRREVERSIBLE_TOOLS and not confirmed:
            action_desc = tool_name.replace("_", " ")
            logger.info("[BROKER] Intercepted irreversible action: %s", tool_name)
            pending_action = {
                "tool": tool_name,
                "args": args
            }
            return False, f"This will {action_desc}. Reply 'yes' to confirm.", pending_action
            
        # Execute tool
        from app.tools.registry import ToolRegistry
        try:
            tool = ToolRegistry.get_tool(tool_name)
            res = tool.execute(**args)
            return True, str(res), {}
        except Exception as e:
            logger.error("[BROKER] Execution failed for %s: %s", tool_name, e)
            return True, f"Failed to execute {tool_name}: {e}", {}
