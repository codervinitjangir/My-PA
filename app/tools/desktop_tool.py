import os
import logging
from app.tools.base_tool import BaseTool
from config import IS_CLOUD

logger = logging.getLogger("J.A.R.V.I.S")

class DesktopAppTool(BaseTool):
    name = "open_desktop_app"
    description = "Opens a desktop application on the local OS"

    def execute(self, app_target: str, **kwargs) -> bool:
        if IS_CLOUD:
            from app.websocket_manager import laptop_manager
            logger.info(f"[TOOL] Routing open_app '{app_target}' to laptop via WebSocket")
            resp = laptop_manager.send_and_wait(action="open_app", payload={"target": app_target})
            if resp.get("status") == "success":
                return True
            else:
                logger.error(f"[TOOL] Laptop failed to open {app_target}: {resp.get('message')}")
                return False
        else:
            try:
                os.startfile(app_target)
                return True
            except Exception as e:
                logger.error(f"[TOOL] Failed to open desktop app {app_target}: {e}")
                return False
