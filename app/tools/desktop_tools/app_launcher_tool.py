import os
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class LaunchAppTool(BaseTool):
    name = "launch_app"
    description = "Launches local desktop applications (like Chrome, VSCode, Notepad) using dynamic routing."
    
    APP_MAP = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "chrome": "chrome.exe",
        "vscode": "code",
        "code": "code"
    }
    
    def execute(self, app_name: str, **kwargs) -> dict:
        app_lower = app_name.lower().strip()
        
        # Use semantic mapping over hardcoded ifs
        target = self.APP_MAP.get(app_lower)
        if not target:
            target = app_name  # Attempt direct invocation if not mapped
            
        logger.info(f"[LAUNCHER] Attempting to launch '{target}'")
        try:
            os.startfile(target)
            return {"status": "success", "message": f"Launched {target}"}
        except Exception as e:
            logger.error(f"[LAUNCHER] Failed to launch {target}: {e}")
            return {"status": "error", "message": f"Could not launch {target}: {e}"}
