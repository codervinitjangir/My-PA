import os
import time
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class TakeScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Takes a screenshot of the user's current desktop and saves it to a file."
    
    def execute(self, filename: str = None, **kwargs) -> dict:
        try:
            import pyautogui
        except ImportError:
            logger.error("[SCREENSHOT] pyautogui is not installed.")
            return {"status": "error", "message": "pyautogui library is missing."}
            
        save_dir = os.path.join(os.getcwd(), "captures")
        os.makedirs(save_dir, exist_ok=True)
        
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        if not filename.endswith(".png"):
            filename += ".png"
            
        filepath = os.path.join(save_dir, filename)
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            logger.info(f"[SCREENSHOT] Saved to {filepath}")
            return {"status": "success", "filepath": filepath}
        except Exception as e:
            logger.error(f"[SCREENSHOT] Failed to capture: {e}")
            return {"status": "error", "message": str(e)}
