from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from contextlib import asynccontextmanager
import uvicorn
import logging
import json
import time
import re
import base64
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import edge_tts
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.models import ChatRequest, ChatResponse, TTSRequest
from pydantic import BaseModel
from typing import Optional

RATE_LIMIT_MESSAGE = (
    "You've reached your daily API limit for this assistant. "
    "Your credits will reset in a few hours, or you can upgrade your plan for more. "
    "Please try again later."
)

def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in str(exc) or "rate limit" in msg or "tokens per day" in msg

from app.services.vector_store import VectorStoreService
from app.providers.groq_provider import GroqProvider as GroqService, AllGroqApisFailedError
from app.services.chat_service import ChatService
from app.services.brain_service import BrainService
from app.services.task_executor import TaskExecutor
from app.services.vision_service import VisionService
from app.services.task_manager import TaskManager
from app.services.stt_service import STTService

import app.tools   # Core OS tools
import app.plugins # Third-party / fun plugins
from app.scheduler import init_scheduler, shutdown_scheduler, LAST_BRIEFING
import app.scheduler as scheduler_module

from config import (
    VECTOR_STORE_DIR, GROQ_API_KEYS, GROQ_MODEL, TAVILY_API_KEY,
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHAT_HISTORY_TURNS,
    ASSISTANT_NAME, TTS_VOICE, TTS_RATE,
    VOICE_PROVIDER, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    ELEVENLABS_STABILITY, ELEVENLABS_SIMILARITY, ELEVENLABS_STYLE, ELEVENLABS_SPEAKER_BOOST
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("J.A.R.V.I.S")
vector_store_service: VectorStoreService = None
groq_service: GroqService = None
brain_service: BrainService = None
task_executor: TaskExecutor = None
task_manager: TaskManager = None
vision_service: VisionService = None
chat_service: ChatService = None
stt_service: STTService = None
request_router = None

def print_title():
    """Print the J.A.R.V.I.S ASCII art title."""
    title = """
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║         ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗          ║
   ║         ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝          ║
   ║         ██║███████║██████╔╝██║   ██║██║███████╗          ║
   ║    ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║          ║
   ║    ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║          ║
   ║     ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝          ║
   ║                                                          ║
   ║          Just A Rather Very Intelligent System           ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝
    """

    try:
        print(title)
    except UnicodeEncodeError:
        # Fallback to a simpler title if the console doesn't support the box characters
        print("\n" + "="*60)
        print("                 J.A.R.V.I.S")
        print("    Just A Rather Very Intelligent System")
        print("="*60 + "\n")

@asynccontextmanager

async def lifespan(app: FastAPI):

    global vector_store_service, groq_service, realtime_service, brain_service
    global task_executor, task_manager, vision_service, chat_service, stt_service
    print_title()
    logger.info("-" * 60)
    logger.info("J.A.R.V.I.S - Starting Up...")
    logger.info("-" * 60)
    logger.info("[CONFIG] Assistant name: %s", ASSISTANT_NAME)
    logger.info("[CONFIG] Groq model: %s", GROQ_MODEL)
    logger.info("[CONFIG] Groq API keys loaded: %d", len(GROQ_API_KEYS))
    logger.info("[CONFIG] Tavily API key: %s", "configured" if TAVILY_API_KEY else "NOT SET")
    logger.info("[CONFIG] Image generation: Pollinations.ai (free, no API key)")
    logger.info("[CONFIG] Embedding model: %s", EMBEDDING_MODEL)
    logger.info("[CONFIG] Chunk size: %d | Overlap: %d | Max history turns: %d",
                CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHAT_HISTORY_TURNS)

    try:

        logger.info("Initializing vector store service...")
        t0 = time.perf_counter()
        try:
            vector_store_service = VectorStoreService()
            vector_store_service.create_vector_store()
            logger.info("[TIMING] startup_vector_store: %.3fs", time.perf_counter() - t0)
        except Exception as e:
            logger.warning(f"VectorStore initialization failed: {e}")
            logger.warning("JARVIS will start without long-term memory (vector store unavailable).")
            vector_store_service = None
        logger.info("Initializing Groq service (general queries)...")
        groq_service = GroqService(vector_store_service)
        logger.info("Groq service initialized successfully")
        logger.info("Initializing Brain service (Groq query classification)...")
        brain_service = BrainService(groq_service)
        logger.info("Brain service initialized successfully")
        logger.info("Initializing Task executor...")
        task_executor = TaskExecutor(groq_service)
        logger.info("Task executor initialized successfully")
        logger.info("Initializing Background task manager...")
        task_manager = TaskManager(task_executor)
        logger.info("Background task manager initialized successfully")
        logger.info("Initializing Vision service (Groq)...")
        vision_service = VisionService()
        logger.info("Vision service initialized successfully")
        
        logger.info("Initializing background scheduler...")
        init_scheduler(groq_service)
        logger.info("Initializing Orchestrator and Agents...")
        from app.core.orchestrator.orchestrator import Orchestrator
        from app.agents.research_agent import DeepResearchAgent
        
        orchestrator = Orchestrator(brain_service)
        research_agent = DeepResearchAgent(groq_service)
        orchestrator.register_agent(research_agent)
        logger.info("Orchestrator initialized successfully")

        logger.info("Initializing chat service...")

        chat_service = ChatService(
            groq_service, brain_service,
            task_executor=task_executor,
            vision_service=vision_service,
            task_manager=task_manager,
            orchestrator=orchestrator,
        )

        from jarvis_os.core.operator_runtime import OperatorRuntime
        from jarvis_os.core.request_router import RequestRouter
        operator_runtime = OperatorRuntime(groq_service)
        global request_router
        request_router = RequestRouter(chat_service, operator_runtime)

        logger.info("Chat service initialized successfully")
        logger.info("Initializing STT service (Groq Whisper)...")
        stt_service = STTService()
        logger.info("STT service initialized: %s", "ready" if stt_service.is_available else "no API key")
        logger.info("-" * 60)
        logger.info("Service Status:")
        logger.info("  - Vector Store: Ready")
        logger.info("  - Groq AI (General & Search): Ready")
        logger.info("  - Brain (Unified Decision): Ready")
        logger.info("  - Task Executor: Ready")
        logger.info("  - Background Task Manager: Ready")
        logger.info("  - Vision (Groq): Ready")
        logger.info("  - STT (Groq Whisper): %s", "Ready" if stt_service and stt_service.is_available else "Not available")
        logger.info("  - Chat Service: Ready")
        
        # Wake Word Initialization
        try:
            from jarvis_os.core.wake_word import init_wake_word_daemon
            init_wake_word_daemon(chat_service, stt_service)
            logger.info("  - Wake Word Daemon: Ready")
        except ImportError:
            logger.warning("  - Wake Word Daemon: Module not found, skipping")
        
        logger.info("-" * 60)
        logger.info("J.A.R.V.I.S is online and ready!")
        logger.info("API: http://localhost:8000")
        logger.info("Frontend: http://localhost:8000/app/ (open in browser)")
        logger.info("-" * 60)

        yield

    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        raise

    finally:
        logger.info("\nShutting down J.A.R.V.I.S...")
        try:
            _tts_pool.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error shutting down TTS pool: {e}")

        if task_manager:
            try:
                task_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down task manager: {e}")
                
        if task_executor:
            try:
                task_executor.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down task executor: {e}")
            
        try:
            from jarvis_os.core.wake_word import shutdown_wake_word_daemon
            shutdown_wake_word_daemon()
        except Exception as e:
            logger.error(f"Error shutting down wake word daemon: {e}")

        if chat_service:
            for session_id in list(chat_service.sessions.keys()):
                try:
                    chat_service.save_chat_session(session_id)
                except Exception as e:
                    logger.error(f"Error saving session {session_id}: {e}")

        try:
            shutdown_scheduler()
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")

        logger.info("All sessions saved. Goodbye!")

        try:
            from jarvis_os.core.usage import flush_usage
            flush_usage()
            logger.info("Usage data flushed to disk.")
        except Exception as e:
            logger.error(f"Error flushing usage data: {e}")


app = FastAPI(
    title="J.A.R.V.I.S API",
    description="Just A Rather Very Intelligent System",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Singleton state manager — persists screen state between requests
from jarvis_os.core.state_manager import GlobalStateManager
_state_mgr = GlobalStateManager()

# ── Security: CORS locked to localhost only ───────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-JARVIS-Token"],
)

# ── Security: Bearer token auth (only active when JARVIS_API_TOKEN is set) ────
_JARVIS_TOKEN = os.getenv("JARVIS_API_TOKEN", "").strip()
_AUTH_PUBLIC_PATHS = {"/", "/health", "/api/config"}
_AUTH_PUBLIC_PREFIXES = ("/app",)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _AUTH_PUBLIC_PATHS:
            return await call_next(request)
        if any(path.startswith(p) for p in _AUTH_PUBLIC_PREFIXES):
            return await call_next(request)

        if not _JARVIS_TOKEN:
            # Enforce localhost only when no token is configured
            client_host = request.client.host if request.client else ""
            if client_host not in ("127.0.0.1", "::1", "localhost"):
                return Response("Unauthorized: Server requires an API token for external access", status_code=401)
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth == f"Bearer {_JARVIS_TOKEN}":
            return await call_next(request)
        return Response("Unauthorized", status_code=401, headers={"WWW-Authenticate": "Bearer"})

app.add_middleware(AuthMiddleware)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - t0
        path = request.url.path
        if path not in ["/api/wake-word/status", "/usage", "/health"]:
            logger.info("[REQUEST] %s %s -> %s (%.3fs)", request.method, path, response.status_code, elapsed)
        return response

# Also silence Uvicorn's default access logger for these endpoints
import logging
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return all(path not in record.getMessage() for path in ["/api/wake-word/status", "/usage", "/health"])

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

app.add_middleware(TimingMiddleware)

@app.get("/api/config")
async def get_frontend_config(request: Request):
    """Returns the API token to localhost callers so the frontend can self-configure."""
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="Config only accessible from localhost")
    from config import ASSISTANT_NAME
    return {"token": _JARVIS_TOKEN, "assistant_name": ASSISTANT_NAME}

@app.get("/api")

async def api_info():
    return {
        "message": "J.A.R.V.I.S API",
        "endpoints": {
            "/chat": "General chat (non-streaming)",
            "/chat/stream": "General chat (streaming chunks)",
            "/chat/realtime": "Realtime chat (non-streaming)",
            "/chat/realtime/stream": "Realtime chat (streaming chunks)",
            "/chat/jarvis/stream": "Jarvis unified route (two-stage brain: classify + route + execute/stream)",
            "/chat/history/{session_id}": "Get chat history",
            "/tasks/{task_id}": "Get background task status and result",
            "/health": "System health check",
            "/tts": "Text-to-speech (POST text, returns streamed MP3)",
            "/stt": "Speech-to-text (POST audio file, returns transcribed text via Groq Whisper)",
        }
    }

@app.get("/dashboard")
async def get_dashboard():
    """Returns the sub-100ms programmatic dashboard state."""
    from jarvis_os.dashboard.dashboard_manager import DashboardManager
    from jarvis_os.core.quick_links import QUICK_LINKS, get_top_sites
    from jarvis_os.core.usage import track_event
    
    track_event("dashboard_open")
    manager = DashboardManager()
    data = manager.get_dashboard()
    
    # Inject wake word status
    try:
        from jarvis_os.core.wake_word import get_wake_word_daemon
        daemon = get_wake_word_daemon()
        data["wake_word"] = {
            "enabled": daemon.enabled if daemon else False,
            "last_wake": daemon.last_wake if daemon else None
        }
    except ImportError:
        data["wake_word"] = {"enabled": False, "last_wake": None}
    return data

@app.get("/mobile/state")
async def get_mobile_state():
    """Minimal state endpoint for Android Companion."""
    from jarvis_os.dashboard.dashboard_manager import DashboardManager
    manager = DashboardManager()
    dash = manager.get_dashboard()
    
    # Map to the strict required response
    screen_state = _state_mgr.mock_states.get("screen", {})
    activity = screen_state.get("activity", "Unknown") if isinstance(screen_state, dict) else "Unknown"

    return {
        "greeting": dash.get("greeting", "Hello Boss"),
        "current_project": dash.get("active_project", "No active project"),
        "current_focus": dash.get("current_focus", "No focus set"),
        "pending_count": dash.get("pending_items", 0),
        "workspace": "Jarvis",
        "active_session": True,
        "screen_activity": activity
    }


@app.get("/briefing")
async def get_briefing():
    """Returns the sub-50ms programmatic daily brief state."""
    from jarvis_os.daily_brief.daily_brief_manager import DailyBriefManager
    from jarvis_os.core.usage import track_event
    track_event("morning_brief")
    manager = DailyBriefManager()
    return manager.get_briefing()

class OperatorActionRequest(BaseModel):
    action: str
    payload: Optional[dict] = None

@app.post("/operator/action")
async def operator_action(request: OperatorActionRequest):
    """
    Unified endpoint for Operator UI actions.
    """
    from jarvis_os.desktop_action.desktop_action_manager import DesktopActionManager
    
    if request.action == "toggle_wake_word":
        try:
            from jarvis_os.core.wake_word import get_wake_word_daemon
            daemon = get_wake_word_daemon()
            if daemon:
                new_state = daemon.toggle()
                return {"success": True, "message": "Wake Word Toggled", "enabled": new_state}
        except ImportError:
            pass
        return {"success": False, "message": "Wake Word Daemon missing"}
        
    if request.action == "open_site":
        site_alias = request.payload.get("site", "") if request.payload else ""
        if site_alias:
            from jarvis_os.core.usage import track_event, track_site
            track_event("browser_open")
            track_site(site_alias)
            
        manager = DesktopActionManager()
        # Not simulating by default when clicking UI links
        result = manager.process_request("open_site", site_alias, user_approved=True, simulate=False)
        return {"success": result.success, "message": result.message}

    if request.action == "analyze_screen":
        from jarvis_os.observers.screen_observer import ScreenObserver, CooldownError
        from jarvis_os.core.usage import track_event
        from app.services.vision_service import VisionService

        observer = ScreenObserver()
        try:
            # 1. Capture — native PIL screenshot, in-memory only
            image_bytes = observer.capture_screen()

            # 2. Sanitize — base64, no file write
            img_b64 = observer.sanitize_data(image_bytes)
            del image_bytes  # privacy: delete raw bytes immediately

            # 3. Analyze via existing VisionService (Groq Llama 4 Scout)
            vision = VisionService()
            from jarvis_os.observers.screen_observer import _SCREEN_PROMPT
            raw_text = vision.analyze_image(prompt=_SCREEN_PROMPT, img_base64=img_b64)
            del img_b64  # privacy: delete base64 immediately after sending

            # 4. Parse into ScreenState
            screen_state = observer.parse_response(raw_text)

            # 5. Update cooldown timestamp
            observer._last_analyzed = screen_state.timestamp

            # 6. Persist in global state (no image stored — only metadata)
            from jarvis_os.core.state_manager import GlobalStateManager
            _state_mgr.update_runtime_state("screen", screen_state.model_dump())

            # 7. Track usage
            track_event("screen_analysis")

            return screen_state.model_dump()

        except CooldownError as e:
            return {"error": str(e), "cooldown": True}
        except Exception as e:
            logger.warning("[SCREEN] Analysis failed: %s", e)
            return {"error": f"Screen analysis failed: {str(e)}", "cooldown": False}

    if request.action in ("morning_brief", "resume_session", "refresh_dashboard"):
        from jarvis_os.core.usage import track_event
        # Simply acknowledge the action. The backend logs the intent.
        # Future: connect to active websocket to push UI changes to PC dashboard.
        if request.action == "morning_brief": track_event("morning_brief")
        if request.action == "resume_session": track_event("session_resume")
        if request.action == "refresh_dashboard": track_event("dashboard_open")
        
        logger.info(f"[MOBILE] Action received: {request.action}")
        return {"success": True, "message": f"{request.action} acknowledged"}

    return {"success": False, "message": f"Unknown action: {request.action}"}

# ── Telegram Webhook ──────────────────────────────────────────────────────────

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Receives Telegram updates and forwards to telegram_bridge.
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok"}
        
    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        
        if text and chat_id and user_id:
            from jarvis_os.core.telegram_bridge import handle_telegram_command
            import asyncio
            # Fire and forget to not block webhook response
            asyncio.create_task(asyncio.to_thread(handle_telegram_command, chat_id, user_id, text))
            
    return {"status": "ok"}

# ── Friction Log ──────────────────────────────────────────────────────────────

@app.get("/frictions")
async def get_frictions_endpoint():
    """Return all friction items, open first."""
    from jarvis_os.core.friction import get_frictions
    return get_frictions()

@app.post("/frictions")
async def add_friction_endpoint(body: dict):
    """Add a new friction item. Body: { 'text': '...' }"""
    from jarvis_os.core.friction import add_friction
    text = (body.get("text") or "").strip()
    if not text:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="text is required")
    return add_friction(text)

@app.patch("/frictions/{friction_id}")
async def resolve_friction_endpoint(friction_id: str):
    """Mark a friction item as resolved."""
    from jarvis_os.core.friction import resolve_friction
    from fastapi import HTTPException
    item = resolve_friction(friction_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Friction not found")
    return item

@app.delete("/frictions/{friction_id}")
async def delete_friction_endpoint(friction_id: str):
    """Permanently delete a friction item."""
    from jarvis_os.core.friction import delete_friction
    from fastapi import HTTPException
    if not delete_friction(friction_id):
        raise HTTPException(status_code=404, detail="Friction not found")
    return {"deleted": True}

# ── Usage Validation ──────────────────────────────────────────────────────────

@app.get("/usage")
async def get_usage():
    """Returns today's usage summary and all-time totals."""
    from jarvis_os.core.usage import get_today_summary
    return get_today_summary()

@app.get("/health")

async def health():
    """Simple health check endpoint."""
    try:
        return {
            "status": "healthy",
            "vector_store": vector_store_service is not None,
            "groq_service": groq_service is not None,
            "brain_service": brain_service is not None,
            "task_executor": task_executor is not None,
            "task_manager": task_manager is not None,
            "vision_service": vision_service is not None,
            "stt_service": stt_service is not None and stt_service.is_available,
            "chat_service": chat_service is not None
        }

    except Exception as e:
        logger.warning("[API /health] Error: %s", e)
        return {"status": "degraded", "error": str(e)}

@app.get("/api/wake-word/status")
async def wake_word_status():
    """Live wake word daemon state + recent interaction history."""
    try:
        from jarvis_os.core.wake_word import get_wake_word_daemon
        daemon = get_wake_word_daemon()
    except ImportError:
        daemon = None
    if not daemon:
        return {"state": "unavailable", "last_wake": None, "history": []}

    state = "off"
    if daemon.enabled:
        if daemon.thread and daemon.thread.is_alive():
            state = "listening"
        else:
            state = "unavailable"
    
    if getattr(daemon, "_busy", False):
        state = "processing"

    return {
        "state":      state,
        "last_wake":  daemon.last_wake,
        "history":    daemon._history[-10:],
    }


from fastapi import Header
from config import JARVIS_API_KEY

# FIX 3: 10/minute per IP limit
@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(chat_req: ChatRequest, request: Request, x_api_key: Optional[str] = Header(None)):

    # FIX 3: API key auth check
    if JARVIS_API_KEY and x_api_key != JARVIS_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-API-Key header")

    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    logger.info("[API /chat] Incoming | session_id=%s | message_len=%d | message=%.100s",
                chat_req.session_id or "new", len(chat_req.message), chat_req.message)

    try:
        session_id = chat_service.get_or_create_session(chat_req.session_id)
        response_text = request_router.process_request(session_id, chat_req.message)
        chat_service.save_chat_session(session_id)
        logger.info("[API /chat] Done | session_id=%s | response_len=%d", session_id[:12], len(response_text))
        return ChatResponse(response=response_text, session_id=session_id)

    except ValueError as e:
        logger.warning("[API /chat] Invalid session_id: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

    except AllGroqApisFailedError as e:
        logger.error("[API /chat] All Groq APIs failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:

        if _is_rate_limit_error(e):
            logger.warning("[API /chat] Rate limit hit: %s", e)
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)

        logger.error("[API /chat] Error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

from app.utils.stream_utils import _stream_generator, _tts_pool

@app.post("/chat/stream")
@limiter.limit("60/minute")
async def chat_stream(chat_req: ChatRequest, request: Request):
    
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    
    logger.info("[API /chat/stream] Incoming | session_id=%s | message_len=%d | message=%.100s",
                chat_req.session_id or "new", len(chat_req.message), chat_req.message)
    
    try:
        session_id = chat_service.get_or_create_session(chat_req.session_id)
        
        chunk_iter = request_router.process_request_stream(session_id, chat_req.message)
        return StreamingResponse(
            _stream_generator(session_id, chunk_iter, is_realtime=False, tts_enabled=chat_req.tts),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except AllGroqApisFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        
        if _is_rate_limit_error(e):
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)
        
        logger.error("[API /chat/stream] Error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/realtime", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat_realtime(chat_req: ChatRequest, request: Request):
    
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")
    
    logger.info("[API /chat/realtime] Incoming | session_id=%s | message_len=%d | message=%.100s",
                chat_req.session_id or "new", len(chat_req.message), chat_req.message)
    
    try:
        session_id = chat_service.get_or_create_session(chat_req.session_id)
        response_text = chat_service.process_realtime_message(session_id, chat_req.message)
        chat_service.save_chat_session(session_id)
        logger.info("[API /chat/realtime] Done | session_id=%s | response_len=%d", session_id[:12], len(response_text))
        return ChatResponse(response=response_text, session_id=session_id)
    
    except ValueError as e:
        logger.warning("[API /chat/realtime] Invalid session_id: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    
    except AllGroqApisFailedError as e:
        logger.error("[API /chat/realtime] All Groq APIs failed: %s", e)
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        
        if _is_rate_limit_error(e):
            logger.warning("[API /chat/realtime] Rate limit hit: %s", e)
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)
        
        logger.error("[API /chat/realtime] Error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.post("/chat/realtime/stream")
@limiter.limit("60/minute")
async def chat_realtime_stream(chat_req: ChatRequest, request: Request):
    
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    logger.info("[API /chat/realtime/stream] Incoming | session_id=%s | message_len=%d | message=%.100s",
                chat_req.session_id or "new", len(chat_req.message), chat_req.message)
    
    try:
        session_id = chat_service.get_or_create_session(chat_req.session_id)
        chunk_iter = chat_service.process_realtime_message_stream(session_id, chat_req.message)
        return StreamingResponse(
            _stream_generator(session_id, chunk_iter, is_realtime=True, tts_enabled=chat_req.tts),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except AllGroqApisFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        
        if _is_rate_limit_error(e):
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)
        
        logger.error("[API /chat/realtime/stream] Error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/jarvis/stream")
@limiter.limit("60/minute")
async def chat_jarvis_stream(chat_req: ChatRequest, request: Request):
    
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    logger.info("[API /chat/jarvis/stream] Incoming | session_id=%s | message_len=%d | img=%s | message=%.100s",
                chat_req.session_id or "new", len(chat_req.message), "yes" if chat_req.imgbase64 else "no", chat_req.message)
    
    try:
        session_id = chat_service.get_or_create_session(chat_req.session_id)
        chunk_iter = chat_service.process_jarvis_message_stream(
            session_id, chat_req.message, imgbase64=chat_req.imgbase64
        )
        
        return StreamingResponse(
            _stream_generator(session_id, chunk_iter, is_realtime=True, tts_enabled=chat_req.tts),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except AllGroqApisFailedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    except Exception as e:
        
        if _is_rate_limit_error(e):
            raise HTTPException(status_code=429, detail=RATE_LIMIT_MESSAGE)
        
        logger.error("[API /chat/jarvis/stream] Error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")

async def get_task_status(task_id: str):
    
    if not task_manager:
        raise HTTPException(status_code=503, detail="Task manager not initialized")
    
    if not task_id or len(task_id) > 32:
        raise HTTPException(status_code=400, detail="Invalid task_id")
        
@app.get("/briefing")
async def get_briefing():
    return {"briefing": scheduler_module.LAST_BRIEFING}
    
    data = task_manager.get_serializable(task_id)
    
    if not data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return data

@app.get("/tasks/{task_id}/image")

async def get_task_image(task_id: str):
    
    if not task_manager:
        raise HTTPException(status_code=503, detail="Task manager not initialized")
    
    if not task_id or len(task_id) > 32:
        raise HTTPException(status_code=400, detail="Invalid task_id")
    
    entry = task_manager.get(task_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if entry.status != "completed" or not entry.image_bytes:
        raise HTTPException(status_code=404, detail="Image not ready")
    
    return Response(content=entry.image_bytes, media_type="image/png")

@app.get("/chat/history/{session_id}")

async def get_chat_history(session_id: str):
    if not chat_service:
        raise HTTPException(status_code=503, detail="Chat service not initialized")

    if not chat_service.validate_session_id(session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    try:
        messages = chat_service.get_chat_history(session_id)
        return {
            "session_id": session_id,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages]
        }

    except Exception as e:
        logger.error(f"Error retrieving history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.post("/tts")

async def text_to_speech(request: TTSRequest):
    text = request.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    async def generate():
        try:
            voice = "hi-IN-MadhurNeural" if is_hindi_text(text) else TTS_VOICE
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=TTS_RATE)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        
        except Exception as e:
            logger.error("[TTS] Error generating speech: %s", e)

    return StreamingResponse(
        generate(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-cache"},
    )

@app.post("/stt")
async def speech_to_text(
    file: "UploadFile",
    language: str = "en",
):
    """
    Speech-to-Text endpoint using Groq Whisper.
    Accepts audio file upload (webm, wav, mp3, ogg, m4a, flac).
    Returns JSON: { text, language, duration, error }
    """
    if not stt_service:
        raise HTTPException(status_code=503, detail="STT service not initialized")

    if not stt_service.is_available:
        raise HTTPException(status_code=503, detail="STT service unavailable. Check GROQ_API_KEY.")

    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided. Send as multipart/form-data field 'file'.")

    # Read audio bytes
    try:
        audio_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {e}")

    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file is empty or too short.")

    filename = file.filename or "audio.webm"

    logger.info("[API /stt] Received audio | file=%s | size=%d bytes | lang=%s",
                filename, len(audio_bytes), language or "auto")

    result = stt_service.transcribe(
        audio_bytes=audio_bytes,
        filename=filename,
        language=language or None,
    )

    if result.get("error") and not result.get("text"):
        logger.warning("[API /stt] Transcription failed: %s", result["error"])
        raise HTTPException(status_code=422, detail=result["error"])

    logger.info("[API /stt] Done | lang=%s | duration=%.1fs | chars=%d",
                result.get("language"), result.get("duration", 0), len(result.get("text", "")))

    return result


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
_react_ui_dir = Path(__file__).resolve().parent.parent / "ui" / "dist"

if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")

if _react_ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_react_ui_dir), html=True), name="react_ui")

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/app/", status_code=302)

def run():
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",   # localhost only — not exposed to network
        port=8000,
        reload=False,       # disabled for stable always-on runtime
        log_level="info"
    )

if __name__ == "__main__":
    run()