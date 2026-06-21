import os
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class DesktopAppTool(BaseTool):
    name = "open_desktop_app"
    description = "Opens a desktop application on the local OS"

    def execute(self, app_target: str, **kwargs) -> bool:
        try:
            os.startfile(app_target)
            return True
        except Exception as e:
            logger.error(f"[TOOL] Failed to open desktop app {app_target}: {e}")
            return False
