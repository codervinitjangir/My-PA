"""
app/core/voice/action_planner.py — Action Dispatcher & Planner

Executes desktop actions instantly when intent confidence exceeds threshold (~100ms post-STT).
Integrates with laptop_manager WebSocket manager and local OS action handles.
"""

import logging
from typing import Dict, Any
from app.core.voice.interfaces import ActionPlanner, IntentPrediction
from app.websocket_manager import laptop_manager

logger = logging.getLogger("J.A.R.V.I.S")

class DesktopActionPlanner(ActionPlanner):
    """
    Action planner for JARVIS desktop commands.
    """
    
    def __init__(self, confidence_threshold: float = 0.85):
        self.confidence_threshold = confidence_threshold

    async def execute_action(self, prediction: IntentPrediction) -> Dict[str, Any]:
        """Execute desktop action if confidence exceeds threshold."""
        if prediction.confidence < self.confidence_threshold:
            logger.info("[ACTION-PLANNER] Skipped action '%s' — confidence %.2f below threshold %.2f",
                        prediction.action, prediction.confidence, self.confidence_threshold)
            return {"success": False, "reason": "low_confidence"}

        action = prediction.action
        target = prediction.target
        params = prediction.parameters or {}
        
        logger.info("[ACTION-PLANNER] Executing action '%s' (target='%s', params=%s, confidence=%.2f)",
                    action, target, params, prediction.confidence)

        # 1. Open App / Web via laptop_manager WebSocket if client connected
        if action in ("open_app", "open_url", "lock_screen", "volume_set", "volume_mute", "volume_unmute", "scroll", "capture_screen"):
            payload = {"target": target, **params}
            if action.startswith("volume_"):
                payload["action"] = action

            command_msg = {
                "action": action if action in ("open_app", "open_url", "capture_screen", "volume_set", "lock_screen", "scroll") else "open_app",
                "payload": payload
            }
            
            if laptop_manager.is_connected():
                res = await laptop_manager.send_and_wait_async(action, payload, timeout=2)
                if res.get("status") == "success" or res.get("success"):
                    return {"success": True, "message": f"Action '{action}' dispatched to laptop client."}
            logger.warning("[ACTION-PLANNER] Laptop client WebSocket unavailable or timed out, attempting local fallback...")

        # 2. Local OS fallback
        try:
            if action == "open_url" and target:
                import webbrowser
                webbrowser.open(target)
                return {"success": True, "message": f"Opened URL {target}"}

            elif action == "open_app" and target:
                import os, subprocess
                try:
                    os.startfile(target)
                except Exception:
                    subprocess.Popen(["start", "", target], shell=True)
                return {"success": True, "message": f"Opened app {target}"}

            elif action == "lock_screen":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return {"success": True, "message": "Screen locked"}

            elif action == "scroll":
                import pyautogui
                direction = params.get("direction", "down")
                amt = params.get("amount", 500)
                scroll_val = amt if direction == "up" else -amt
                pyautogui.scroll(scroll_val)
                return {"success": True, "message": f"Scrolled {direction}"}

        except Exception as e:
            logger.error("[ACTION-PLANNER] Local execution failed: %s", e)
            return {"success": False, "error": str(e)}

        return {"success": True, "message": f"Acknowledged action '{action}'"}
