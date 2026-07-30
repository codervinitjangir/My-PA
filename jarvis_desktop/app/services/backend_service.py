# jarvis_desktop/app/services/backend_service.py

import asyncio
import httpx
from PySide6.QtCore import QObject, Signal

class BackendService(QObject):
    """
    Asynchronous HTTP Service communicating with local FastAPI JARVIS backend (http://127.0.0.1:8000).
    Supports non-blocking health checks, dashboard metrics, briefing reports, operator actions,
    and live real-time token streaming.
    """
    status_changed = Signal(bool)               # True=Online, False=Offline
    dashboard_updated = Signal(dict)           # Emits dashboard data
    chat_chunk_received = Signal(str)           # Emits individual streaming text token
    chat_response_received = Signal(dict)       # Emits completed chat payload response
    briefing_received = Signal(dict)            # Emits briefing payload
    action_completed = Signal(dict)             # Emits action result
    error_occurred = Signal(str)                # Emits error message

    def __init__(self, base_url: str = "http://127.0.0.1:8000", parent=None):
        super().__init__(parent)
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)

    async def check_health(self) -> bool:
        """Ping backend to update status badge"""
        try:
            resp = await self.client.get("/status")
            is_online = resp.status_code == 200
            self.status_changed.emit(is_online)
            return is_online
        except Exception:
            self.status_changed.emit(False)
            return False

    async def fetch_dashboard(self):
        """Fetch dashboard metrics and state"""
        try:
            resp = await self.client.get("/dashboard")
            if resp.status_code == 200:
                data = resp.json()
                self.dashboard_updated.emit(data)
                self.status_changed.emit(True)
            else:
                self.status_changed.emit(False)
        except Exception as e:
            self.status_changed.emit(False)
            self.error_occurred.emit(f"Dashboard error: {str(e)}")

    async def send_chat_message(self, text: str, mode: str = "jarvis"):
        """Send non-streaming chat message to /chat endpoint"""
        try:
            payload = {
                "message": text,
                "mode": mode,
                "vision_mode": False
            }
            resp = await self.client.post("/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                self.chat_response_received.emit(data)
            else:
                self.error_occurred.emit(f"Chat failed with status {resp.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"Chat error: {str(e)}")

    async def stream_chat_message(self, text: str, mode: str = "jarvis"):
        """Stream real-time token response token-by-token from /chat/jarvis/stream"""
        try:
            payload = {"message": text, "mode": mode}
            endpoint = "/chat/jarvis/stream" if mode == "jarvis" else "/chat/stream"
            
            async with self.client.stream("POST", endpoint, json=payload) as response:
                if response.status_code == 200:
                    accumulated = ""
                    async for chunk in response.aiter_text():
                        if chunk:
                            accumulated += chunk
                            self.chat_chunk_received.emit(chunk)
                    
                    # Emit final payload
                    self.chat_response_received.emit({
                        "response": accumulated,
                        "flow": [
                            {"step": "1", "title": "Query detected", "detail": text},
                            {"step": "2", "title": "Token streaming", "detail": "Completed token stream"}
                        ]
                    })
                else:
                    # Fallback to non-streaming endpoint if streaming endpoint is unavailable
                    await self.send_chat_message(text, mode)
        except Exception:
            # Fallback to standard chat endpoint
            await self.send_chat_message(text, mode)

    async def fetch_briefing(self):
        """Fetch daily briefing report"""
        try:
            resp = await self.client.get("/briefing")
            if resp.status_code == 200:
                self.briefing_received.emit(resp.json())
        except Exception as e:
            self.error_occurred.emit(f"Briefing error: {str(e)}")

    async def execute_operator_action(self, action_name: str, payload: dict = None):
        """Execute operator action (e.g. open site, toggle wake word)"""
        try:
            body = {"action": action_name}
            if payload:
                body["payload"] = payload
            resp = await self.client.post("/operator/action", json=body)
            if resp.status_code == 200:
                self.action_completed.emit(resp.json())
        except Exception as e:
            self.error_occurred.emit(f"Action error: {str(e)}")

    async def close(self):
        """Close HTTP client session"""
        await self.client.aclose()
