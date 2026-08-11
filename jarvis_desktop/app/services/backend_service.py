# jarvis_desktop/app/services/backend_service.py

from rich import json
import asyncio
import os
import httpx
import webbrowser
import ctypes
from dotenv import load_dotenv
from PySide6.QtCore import QObject, Signal

load_dotenv()

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
    latency_updated = Signal(dict)              # Emits latency metrics

    def __init__(self, base_url: str = "http://127.0.0.1:8000", parent=None):
        super().__init__(parent)
        self.base_url = base_url
        auth_token = os.getenv("JARVIS_API_TOKEN", "") or os.getenv("JARVIS_API_KEY", "") or "jarvis-auth-token-98f2c7a3"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS-Desktop/1.0",
            "Authorization": f"Bearer {auth_token}",
            "X-API-Key": auth_token,
            "X-JARVIS-Token": auth_token,
        }
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)
        import time
        self.last_activity = time.time()

    async def check_proactive(self):
        """Called every 30s by main loop. If silent for 15+ mins, ping proactive engine."""
        import time
        if time.time() - self.last_activity > 900:  # 15 mins
            self.last_activity = time.time() # Reset to avoid spamming
            try:
                resp = await self.client.get("/proactive/check")
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("message", "").strip()
                    if msg:
                        # Emulate a chat response so the GUI displays and speaks it
                        self.chat_response_received.emit({
                            "response": msg,
                            "flow": []
                        })
            except Exception as e:
                pass

    async def check_health(self) -> bool:
        """Ping backend to update status badge quietly"""
        try:
            resp = await self.client.get("/health")
            is_online = resp.status_code == 200
            self.status_changed.emit(is_online)
            return is_online
        except Exception:
            self.status_changed.emit(False)
            return False

    async def fetch_dashboard(self):
        """Fetch dashboard metrics and live usage telemetry from /dashboard and /usage"""
        try:
            print("[BackendService] GET http://127.0.0.1:8000/dashboard ...")
            resp = await self.client.get("/dashboard")
            print(f"[BackendService] GET /dashboard -> HTTP {resp.status_code}")

            print("[BackendService] GET http://127.0.0.1:8000/usage ...")
            usage_resp = await self.client.get("/usage")
            print(f"[BackendService] GET /usage -> HTTP {usage_resp.status_code}")

            data = resp.json() if resp.status_code == 200 else {}
            events = {}
            if usage_resp.status_code == 200:
                u_data = usage_resp.json()
                events = u_data.get("events", {}) or u_data.get("features", {}) or {}

            data["metrics"] = {
                "Dashboard": events.get("dashboard_open", 1),
                "Morning Brief": events.get("morning_brief", 0),
                "Screen Analysis": events.get("screen_analysis", 0),
                "Resume Session": events.get("resume_session", 0),
                "Browser Opens": events.get("browser_open", 0),
            }
            self.dashboard_updated.emit(data)
            self.status_changed.emit(True)
        except Exception as e:
            print(f"[BackendService] Dashboard error: {e}")
            self.status_changed.emit(False)
            self.error_occurred.emit(f"Dashboard error: {str(e)}")

    async def send_chat_message(self, text: str, mode: str = "jarvis"):
        """Send non-streaming chat message to /chat endpoint"""
        import time
        self.last_activity = time.time()
        try:
            print(f"[BackendService] POST http://127.0.0.1:8000/chat | payload: '{text[:50]}' ...")
            payload = {
                "message": text,
                "mode": mode,
                "vision_mode": False
            }
            resp = await self.client.post("/chat", json=payload)
            print(f"[BackendService] POST /chat -> HTTP {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"[BackendService] Received response ({len(data.get('response', ''))} chars)")
                self.chat_response_received.emit(data)
            else:
                self.error_occurred.emit(f"Chat failed with status {resp.status_code}")
        except Exception as e:
            print(f"[BackendService] Chat error: {e}")
            self.error_occurred.emit(f"Chat error: {str(e)}")

    async def stream_chat_message(self, text: str, mode: str = "jarvis", is_voice: bool = False):
        """Stream real-time token response token-by-token from /chat/jarvis/stream"""
        import time
        self.last_activity = time.time()
        try:
            payload = {"message": text, "mode": mode, "is_voice_mode": is_voice}
            endpoint = "/chat/jarvis/stream" if mode == "jarvis" else "/chat/stream"

            async with self.client.stream("POST", endpoint, json=payload) as response:
                if response.status_code == 200:
                    accumulated = ""
                    flow_steps = []
                    step_count = 1

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("data:"):
                            line = line[5:].strip()

                        try:
                            data = json.loads(line)
                            # Extract clean text chunk token
                            if "chunk" in data and data["chunk"]:
                                chunk_text = str(data["chunk"])
                                accumulated += chunk_text
                                self.chat_chunk_received.emit(chunk_text)

                            # Extract activity flow events
                            if "activity" in data and isinstance(data["activity"], dict):
                                act = data["activity"]
                                evt = act.get("event", "")
                                msg = act.get("message", act.get("route", evt))
                                flow_steps.append({"step": str(step_count), "title": evt, "detail": str(msg)})
                                step_count += 1

                            # Extract and safely execute local actions
                            if "actions" in data and isinstance(data["actions"], dict):
                                actions = data["actions"]
                                import webbrowser
                                import os
                                import sys
                                # Ensure we can import from app.core.security
                                if ".." not in sys.path and "." not in sys.path:
                                    sys.path.append(os.path.abspath("."))
                                try:
                                    from app.core.security.allowlist import is_safe_url, is_safe_app_target
                                except ImportError:
                                    # Fallback strict functions if import fails
                                    is_safe_url = lambda u: (u.startswith("http"), u)
                                    is_safe_app_target = lambda a: (False, "Security import failed")

                                # Handle web links and app protocol launches
                                for url in actions.get("wopens", []) + actions.get("plays", []) + actions.get("googlesearches", []) + actions.get("youtubesearches", []):
                                    if url.startswith("http"):
                                        safe, target = is_safe_url(url)
                                        if safe:
                                            webbrowser.open(target)
                                        else:
                                            print(f"[BackendService] Blocked unsafe URL: {url} - {target}")
                                    elif url.startswith("app:"):
                                        app_name = url.split(":", 1)[1]
                                        safe, target = is_safe_app_target(app_name)
                                        if safe:
                                            try:
                                                os.startfile(target)
                                            except Exception as e:
                                                print(f"[BackendService] App launch error: {e}")
                                        else:
                                            print(f"[BackendService] Blocked unsafe App: {app_name} - {target}")
                                            
                                # Handle explicit desktop apps
                                for app in actions.get("desktop_apps", []):
                                    safe, target = is_safe_app_target(app)
                                    if safe:
                                        try:
                                            if target in ("lock_screen", "system:lock_screen", "lock_pc", "lock"):
                                                ctypes.windll.user32.LockWorkStation()
                                            else:
                                                os.startfile(target)
                                        except Exception as e:
                                            print(f"[BackendService] App launch error: {e}")
                                    else:
                                        print(f"[BackendService] Blocked unsafe App: {app} - {target}")

                            if data.get("done") is True and not data.get("chunk"):
                                break
                        except Exception:
                            pass

                    # Emit final completed chat payload
                    self.chat_response_received.emit({
                        "response": accumulated,
                        "flow": flow_steps
                    })
                else:
                    await self.send_chat_message(text, mode)
        except Exception:
            await self.send_chat_message(text, mode)

    async def fetch_briefing(self):
        """Fetch daily briefing report"""
        try:
            resp = await self.client.get("/briefing")
            if resp.status_code == 200:
                self.briefing_received.emit(resp.json())
        except Exception as e:
            self.error_occurred.emit(f"Briefing error: {str(e)}")

    async def fetch_latency(self):
        import time
        start_time = time.time()
        try:
            resp = await self.client.get("/api/latency/dashboard", timeout=2.0)
            ping = (time.time() - start_time) * 1000
            
            data = {"ping": ping}
            if resp.status_code == 200:
                json_data = resp.json()
                pct = json_data.get("percentiles", {})
                if pct:
                    ttfa_pct = pct.get("ttfa_ms", {})
                    data["p50"] = ttfa_pct.get("P50", 0)
                    data["p95"] = ttfa_pct.get("P95", 0)
                    data["p99"] = ttfa_pct.get("P99", 0)
            
            self.latency_updated.emit(data)
        except Exception:
            self.latency_updated.emit({"ping": "--", "p50": "--", "p95": "--", "p99": "--"})

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

    async def transcribe_audio(self, wav_bytes: bytes) -> str:
        """Send audio bytes to /stt endpoint for speech-to-text transcription"""
        try:
            files = {'file': ('audio.wav', wav_bytes, 'audio/wav')}
            resp = await self.client.post("/stt", files=files)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("text", "").strip()
            else:
                self.error_occurred.emit(f"STT failed with status {resp.status_code}")
                return ""
        except Exception as e:
            self.error_occurred.emit(f"STT error: {str(e)}")
            return ""

    async def analyze_vision(self, image_b64: str, prompt: str = "Analyze this screen screenshot and summarize key items"):
        """Send screen capture base64 image to vision chat endpoint"""
        try:
            payload = {
                "message": f"[Screen Capture Analysis] {prompt}",
                "image_b64": image_b64,
                "vision_mode": True
            }
            resp = await self.client.post("/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                self.chat_response_received.emit(data)
            else:
                self.error_occurred.emit(f"Vision analysis failed with status {resp.status_code}")
        except Exception as e:
            self.error_occurred.emit(f"Vision error: {str(e)}")

    async def synthesize_speech(self, text: str) -> bytes:
        """Fetch TTS audio bytes from /tts endpoint"""
        try:
            resp = await self.client.post("/tts", json={"text": text})
            if resp.status_code == 200:
                return resp.content
            return b""
        except Exception as e:
            self.error_occurred.emit(f"TTS error: {str(e)}")
            return b""

    async def close(self):
        """Close HTTP client session"""
        await self.client.aclose()
