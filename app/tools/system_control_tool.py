import logging
from typing import Dict, Any
from app.tools.base_tool import BaseTool
from config import IS_CLOUD

logger = logging.getLogger("J.A.R.V.I.S")

class SystemControlTool(BaseTool):
    name = "system_control"
    description = """
    Controls system settings on the user's local OS.
    Supported actions:
    - lock_screen: Locks the computer.
    - volume_set: Sets volume level (requires 'level' 0-100).
    - volume_mute / volume_unmute: Mutes or unmutes audio.
    - brightness_set: Sets screen brightness (requires 'level' 0-100).
    - wifi_toggle: Turns WiFi on or off (requires 'state'="on" or "off").
    """

    def execute(self, action: str, level: int = None, state: str = None, **kwargs) -> str:
        payload = {}
        if level is not None:
            payload["level"] = level
        if state is not None:
            payload["state"] = state

        if IS_CLOUD:
            from app.websocket_manager import laptop_manager
            logger.info(f"[TOOL] Routing system action '{action}' to laptop via WebSocket")
            resp = laptop_manager.send_and_wait(action=action, payload=payload)
            if resp.get("success") or resp.get("status") == "success":
                return f"Successfully executed {action}."
            else:
                err = resp.get('error') or resp.get('message', 'Unknown error')
                return f"Failed to execute {action}: {err}"
        else:
            return "System control from local backend is not fully implemented yet. Please use Cloud mode with laptop_client."
