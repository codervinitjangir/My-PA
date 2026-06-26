import json
import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import List, Optional, Dict, Iterator, Any, Union
import uuid
import threading

from config import CHATS_DATA_DIR, MAX_CHAT_HISTORY_TURNS, GROQ_API_KEYS
from app.models import ChatMessage
from app.providers.groq_provider import GroqProvider as GroqService
from app.services.brain_service import BrainService
from app.core.orchestrator.orchestrator import Orchestrator
from app.services.task_executor import TaskExecutor
from app.services.vision_service import VisionService
from app.services.task_manager import TaskManager
from app.services.decision_types import HEAVY_INTENTS, INSTANT_INTENTS
from app.utils.key_rotation import get_next_key_pair

logger = logging.getLogger("J.A.R.V.I.S")

JARVIS_BRAIN_SEARCH_TIMEOUT = 15
SAVE_EVERY_N_CHUNKS = 5


class ChatService:
    def __init__(
        self,
        groq_service: GroqService,
        brain_service: BrainService = None,
        task_executor: TaskExecutor = None,
        vision_service: VisionService = None,
        task_manager: TaskManager = None,
        orchestrator: Orchestrator = None,
    ):
        self.groq_service = groq_service
        self.brain_service = brain_service
        self.task_executor = task_executor
        self.vision_service = vision_service
        self.task_manager = task_manager
        self.orchestrator = orchestrator
        self._state_mgr = None
        self.sessions: Dict[str, List[ChatMessage]] = {}
        self._save_lock = threading.Lock()

    def set_state_manager(self, state_mgr) -> None:
        """Inject the GlobalStateManager so chat can read live screen state."""
        self._state_mgr = state_mgr

    def _build_screen_context(self) -> str:
        """
        Reads last screen analysis from GlobalStateManager.
        Returns a formatted context block if fresh (< 5 min old), else empty string.
        Silently returns "" on any error — never breaks chat.
        """
        try:
            if not self._state_mgr:
                return ""
            global_state = self._state_mgr.build_global_state()
            screen = global_state.get("screen")
            if not screen:
                return ""
            import time
            age_seconds = time.time() - screen.get("timestamp", 0)
            if age_seconds > 300:   # older than 5 minutes — skip
                return ""
            app  = screen.get("application", "Unknown")
            act  = screen.get("activity", "Unknown")
            conf = screen.get("confidence", 0)
            summ = screen.get("summary", "")
            nxt  = screen.get("next_best_action", "")
            age_str = f"{int(age_seconds)}s ago"
            return (
                f"\n[SCREEN CONTEXT — analyzed {age_str}]\n"
                f"Application: {app} | Activity: {act} | Confidence: {conf:.0f}%\n"
                f"Summary: {summ}\n"
                f"Suggested next action: {nxt}\n"
                f"[END SCREEN CONTEXT]\n"
            )
        except Exception:
            return ""

    def update_vector_store_live(self, session_id: str):
        vss = getattr(self.groq_service, 'vector_store_service', None)
        if not vss or not vss.vector_store:
            return
            
        messages = self.sessions.get(session_id, [])
        if len(messages) >= 2:
            last_user = messages[-2]
            last_assistant = messages[-1]
            if last_user.role == "user" and last_assistant.role == "assistant":
                chat_content = f"User: {last_user.content}\nAssistant: {last_assistant.content}"
                if chat_content.strip():
                    from langchain_core.documents import Document
                    import time
                    ts = time.time()
                    safe_session_id = session_id.replace("-", "").replace(".", "_")
                    doc = Document(page_content=chat_content, metadata={"source": f"chat_{safe_session_id}", "timestamp": ts})
                    try:
                        vss.vector_store.add_documents([doc])
                        vss.save_vector_store()
                        logger.info(f"[VECTOR] Live indexed new chat turn for session {session_id[:12]}")
                    except Exception as e:
                        logger.warning(f"Failed to update vector store live: {e}")

    def load_session_from_disk(self, session_id: str) -> bool:
        safe_session_id = session_id.replace("-", "").replace(".", "_")
        filename = f"chat_{safe_session_id}.json"
        filepath = CHATS_DATA_DIR / filename

        if not filepath.exists():
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                chat_dict = json.load(f)

            messages = []
            for msg in chat_dict.get("messages", []):
                if not isinstance(msg, dict):
                    continue
                
                role = msg.get("role")
                role = role if role in ("user", "assistant") else "user"
                
                content = msg.get("content")
                content = content if isinstance(content, str) else str(content or "")
                
                messages.append(
                    ChatMessage(
                        role=role, 
                        content=content
                    )
                )

            self.sessions[session_id] = messages
            return True

        except Exception as e:
            logger.warning(
                "Failed to load session %s from disk: %s", 
                session_id, 
                e
            )
            return False



    def validate_session_id(self, session_id: str) -> bool:
        if not session_id or not isinstance(session_id, str):
            return False
        if session_id == "telegram":
            return True
        # Enforce strict UUID4 format
        return bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', session_id, re.IGNORECASE))

    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        t0 = time.perf_counter()

        if not session_id:
            new_session_id = str(uuid.uuid4())
            self.sessions[new_session_id] = []
            logger.info(
                "[TIMING] session_get_or_create: %.3fs (new)", 
                time.perf_counter() - t0
            )
            return new_session_id

        if not self.validate_session_id(session_id):
            raise ValueError(
                f"Invalid session_id format: {session_id}. Session ID must be non-empty, "
                "not contain path traversal characters, and be under 255 characters."
            )

        if session_id in self.sessions:
            logger.info(
                "[TIMING] session_get_or_create: %.3fs (memory)", 
                time.perf_counter() - t0
            )
            return session_id

        if self.load_session_from_disk(session_id):
            logger.info(
                "[TIMING] session_get_or_create: %.3fs (disk)", 
                time.perf_counter() - t0
            )
            return session_id

        self.sessions[session_id] = []
        logger.info(
            "[TIMING] session_get_or_create: %.3fs (new_id)", 
            time.perf_counter() - t0
        )
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append(
            ChatMessage(
                role=role, 
                content=content
            )
        )

    def get_chat_history(self, session_id: str) -> List[ChatMessage]:
        return self.sessions.get(session_id, [])

    def format_history_for_llm(self, session_id: str, exclude_last: bool = False) -> List[tuple]:
        messages = self.get_chat_history(session_id)
        history = []
        messages_to_process = messages[:-1] if exclude_last and messages else messages

        i = 0
        while i < len(messages_to_process) - 1:
            user_msg = messages_to_process[i]
            ai_msg = messages_to_process[i + 1]

            if user_msg.role == "user" and ai_msg.role == "assistant":
                u_content = user_msg.content if isinstance(user_msg.content, str) else str(user_msg.content or "")
                a_content = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content or "")
                
                history.append((u_content, a_content))
                i += 2

            else:
                i += 1

        if len(history) > MAX_CHAT_HISTORY_TURNS:
            history = history[-MAX_CHAT_HISTORY_TURNS:]

        return history

    def process_message(self, session_id: str, user_message: str) -> str:
        logger.info(
            "[GENERAL] Session: %s | User: %.200s", 
            session_id[:12], 
            user_message
        )
        
        self.add_message(session_id, "user", user_message)

        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        
        logger.info(
            "[GENERAL] History pairs sent to LLM: %d", 
            len(chat_history)
        )

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        
        response = self.groq_service.get_response(
            question=user_message, 
            chat_history=chat_history, 
            key_start_index=chat_idx
        )

        self.add_message(session_id, "assistant", response)
        
        logger.info(
            "[GENERAL] Response length: %d chars | Preview: %.120s", 
            len(response), 
            response
        )
        
        self.save_chat_session(session_id)
        self.update_vector_store_live(session_id)
        return response

    def process_realtime_message(self, session_id: str, user_message: str) -> str:

        logger.info(
            "[REALTIME] Session: %s | User: %.200s", 
            session_id[:12], 
            user_message
        )
        
        self.add_message(session_id, "user", user_message)

        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        
        logger.info(
            "[REALTIME] History pairs sent to LLM: %d", 
            len(chat_history)
        )

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        
        response = self.groq_service.get_response(
            question=user_message, 
            chat_history=chat_history, 
            key_start_index=chat_idx,
            use_search=True
        )

        self.add_message(session_id, "assistant", response)
        
        logger.info(
            "[REALTIME] Response length: %d chars | Preview: %.120s", 
            len(response), 
            response
        )
        
        self.save_chat_session(session_id)
        self.update_vector_store_live(session_id)
        return response

    def process_message_stream(
        self, 
        session_id: str, 
        user_message: str
    ) -> Iterator[Union[str, Dict[str, Any]]]:
        
        logger.info(
            "[GENERAL-STREAM] Session: %s | User: %.200s", 
            session_id[:12], 
            user_message
        )
        
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", "")

        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        
        logger.info(
            "[GENERAL-STREAM] History pairs sent to LLM: %d", 
            len(chat_history)
        )

        yield {
            "_activity": {
                "event": "query_detected", 
                "message": user_message
            }
        }
        
        yield {
            "_activity": {
                "event": "routing", 
                "route": "general"
            }
        }
        
        yield {
            "_activity": {
                "event": "streaming_started", 
                "route": "general"
            }
        }

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        chunk_count = 0
        t0 = time.perf_counter()

        try:
            for chunk in self.groq_service.stream_response(
                question=user_message, 
                chat_history=chat_history, 
                key_start_index=chat_idx
            ):
                if isinstance(chunk, dict):
                    yield chunk
                    continue

                if chunk_count == 0:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    yield {
                        "_activity": {
                            "event": "first_chunk", 
                            "route": "general", 
                            "elapsed_ms": elapsed_ms
                        }
                    }

                self.sessions[session_id][-1].content += chunk
                chunk_count += 1

                if chunk_count % SAVE_EVERY_N_CHUNKS == 0:
                    self.save_chat_session(session_id, log_timing=False)

                yield chunk

        finally:
            final_response = self.sessions[session_id][-1].content
            logger.info(
                "[GENERAL-STREAM] Completed | Chunks: %d | Response length: %d chars",
                chunk_count, 
                len(final_response)
            )
            self.save_chat_session(session_id)
            self.update_vector_store_live(session_id)

    def process_realtime_message_stream(
        self, 
        session_id: str, 
        user_message: str
    ) -> Iterator[Union[str, Dict[str, Any]]]:

        logger.info(
            "[REALTIME-STREAM] Session: %s | User: %.200s", 
            session_id[:12], 
            user_message
        )
        
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", "")

        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        
        logger.info(
            "[REALTIME-STREAM] History pairs sent to LLM: %d", 
            len(chat_history)
        )

        yield {
            "_activity": {
                "event": "query_detected", 
                "message": user_message
            }
        }
        
        yield {
            "_activity": {
                "event": "routing", 
                "route": "realtime"
            }
        }
        
        yield {
            "_activity": {
                "event": "streaming_started", 
                "route": "realtime"
            }
        }

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        chunk_count = 0
        t0 = time.perf_counter()

        try:
            for chunk in self.groq_service.stream_response(
                question=user_message, 
                chat_history=chat_history, 
                key_start_index=chat_idx,
                use_search=True
            ):
                if isinstance(chunk, dict):
                    yield chunk
                    continue

                if chunk_count == 0:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    yield {
                        "_activity": {
                            "event": "first_chunk", 
                            "route": "realtime", 
                            "elapsed_ms": elapsed_ms
                        }
                    }

                self.sessions[session_id][-1].content += chunk
                chunk_count += 1

                if chunk_count % SAVE_EVERY_N_CHUNKS == 0:
                    self.save_chat_session(session_id, log_timing=False)

                yield chunk

        finally:
            final_response = self.sessions[session_id][-1].content
            logger.info(
                "[REALTIME-STREAM] Completed | Chunks: %d | Response length: %d chars",
                chunk_count, 
                len(final_response)
            )
            self.save_chat_session(session_id)
            self.update_vector_store_live(session_id)

    def process_jarvis_message_stream(
        self, 
        session_id: str, 
        user_message: str, 
        imgbase64: Optional[str] = None
    ) -> Iterator[Union[str, Dict[str, Any]]]:
        
        # Handle hidden camera bypass token from frontend
        CAM_BYPASS_TOKEN = "TTCAMTOKENTT"
        is_vision_requested = CAM_BYPASS_TOKEN in user_message
        clean_user_message = user_message.replace(CAM_BYPASS_TOKEN, "").strip()
        
        # Intercept /set_model command
        if clean_user_message.startswith("/set_model "):
            new_model = clean_user_message.split(" ", 1)[1].strip()
            logger.info(f"Intercepted /set_model command for model: {new_model}")
            try:
                self.groq_service.set_model(new_model)
                yield f"Model successfully switched to **{new_model}**."
            except Exception as e:
                yield f"Failed to switch model: {e}"
            return

        # Intercept /search_chat command
        if clean_user_message.startswith("/search_chat "):
            query = clean_user_message.split(" ", 1)[1].strip().lower()
            logger.info(f"Intercepted /search_chat command for: {query}")
            matches = []
            for s_id, messages in self.sessions.items():
                for msg in messages:
                    if query in msg.content.lower():
                        matches.append(f"- **{msg.role}**: {msg.content[:100]}...")
            
            if matches:
                yield f"**Search Results:**\n" + "\n".join(matches[:10])
            else:
                yield "No matches found in active session history."
            return
            
        # Intercept /context command
        if clean_user_message.startswith("/context"):
            try:
                from app.memory.user_profile_manager import UserProfileManager
                profile = UserProfileManager().get_profile_summary()
                
                context_msg = f"--- AUTOMATIC CONTEXT INJECTION ---\n{profile}\n-----------------------------------"
                # Insert at the beginning of the session if possible, or just add as system
                self.sessions.get(session_id, []).insert(0, ChatMessage(role="system", content=context_msg))
                yield "Supermemory context successfully injected into the session."
            except Exception as e:
                yield f"Failed to inject context: {e}"
            return
            
        # Intercept /rollback command
        if clean_user_message.startswith("/rollback"):
            try:
                if len(self.sessions.get(session_id, [])) >= 2:
                    self.sessions[session_id].pop()
                    self.sessions[session_id].pop()
                    self.save_chat_session(session_id)
                    yield "Rolled back the last interaction successfully."
                else:
                    yield "Not enough history to rollback."
            except Exception as e:
                yield f"Failed to rollback: {e}"
            return

        # Use clean message for storage and processing
        self.add_message(session_id, "user", clean_user_message)
        self.add_message(session_id, "assistant", "")
        
        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        
        screen_ctx = self._build_screen_context()
        if screen_ctx:
            # Prepend as a system message so LLM sees it but user doesn't
            chat_history = [("system", screen_ctx)] + list(chat_history)
            logger.info("[SCREEN CTX] Injected screen context into chat (age < 5min)")

        yield {
            "_activity": {
                "event": "query_detected", 
                "message": clean_user_message
            }
        }

        brain_idx, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=True)

        query_type = "realtime"
        reasoning = "Defaulting to realtime"
        brain_elapsed_ms = 0
        formatted_results = ""
        search_payload = None

        def _run_brain():
            if self.orchestrator:
                res = self.orchestrator.route_request(clean_user_message, chat_history)
                return (res["category"], res["task_types"], res["method"], res["elapsed_ms"])
            if self.brain_service and brain_idx is not None:
                qt, tasks, r, ms = self.brain_service.classify(
                    clean_user_message, 
                    chat_history, 
                    key_index=brain_idx
                )
                return (qt, tasks, r, ms)
            return ("realtime", [], "No brain service", 0)

        def _run_search():
            return self.groq_service.prefetch_web_search(
                clean_user_message, 
                chat_history
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_brain = executor.submit(_run_brain)
            future_search = executor.submit(_run_search)

            try:
                query_type, tasks, reasoning, brain_elapsed_ms = future_brain.result(
                    timeout=JARVIS_BRAIN_SEARCH_TIMEOUT
                )

            except FuturesTimeoutError:
                logger.warning(
                    "[JARVIS] Brain classification timed out after %ds, defaulting to realtime", 
                    JARVIS_BRAIN_SEARCH_TIMEOUT
                )
                query_type, tasks, reasoning, brain_elapsed_ms = (
                    "realtime", 
                    [], 
                    "Brain timeout, defaulting to realtime", 
                    0
                )

            if query_type == "general":
                formatted_results, search_payload = "", None

            else:
                try:
                    formatted_results, search_payload = future_search.result(
                        timeout=JARVIS_BRAIN_SEARCH_TIMEOUT
                    )

                except FuturesTimeoutError:
                    logger.warning(
                        "[JARVIS] Web search prefetch timed out after %ds", 
                        JARVIS_BRAIN_SEARCH_TIMEOUT
                    )
                    formatted_results, search_payload = "", None

        logger.info(
            "[JARVIS] Brain: %s in %d ms - %s", 
            query_type, 
            brain_elapsed_ms, 
            reasoning
        )

        yield {
            "_activity": {
                "event": "decision", 
                "query_type": query_type, 
                "reasoning": reasoning, 
                "elapsed_ms": brain_elapsed_ms
            }
        }
        
        # Normalize 'camera' to 'vision' and handle triggers
        if query_type == "camera":
            query_type = "vision"
            
        if imgbase64 and query_type in ("general", "realtime"):
            # If we have an image, force vision mode
            query_type = "vision"
            reasoning = "Image provided, forcing vision analysis"

        yield {
            "_activity": {
                "event": "routing", 
                "route": query_type
            }
        }

        if query_type == "realtime" and search_payload:
            yield {
                "_search_results": search_payload
            }

        if query_type == "vision":
            if self.vision_service and imgbase64:
                yield {
                    "_activity": {
                        "event": "vision_processing",
                        "status": "started"
                    }
                }

                v_t0 = time.perf_counter()

                vision_res = self.vision_service.analyze_image(
                    clean_user_message,
                    imgbase64,
                    chat_history
                )

                v_ms = int((time.perf_counter() - v_t0) * 1000)

                yield {
                    "_activity": {
                        "event": "vision_processing",
                        "status": "done",
                        "elapsed_ms": v_ms
                    }
                }

                self.sessions[session_id][-1].content = vision_res
                yield vision_res
                self.save_chat_session(session_id)
                return
            else:
                # User requested vision but no webcam image provided -> fallback to desktop screen capture
                yield {
                    "_activity": {
                        "event": "vision_processing",
                        "status": "capturing_screen"
                    }
                }
                
                try:
                    from jarvis_os.observers.screen_observer import ScreenObserver
                    observer = ScreenObserver()
                    image_bytes = observer.capture_screen()
                    imgbase64 = observer.sanitize_data(image_bytes)
                    del image_bytes
                    
                    v_t0 = time.perf_counter()
                    vision_res = self.vision_service.analyze_image(
                        clean_user_message,
                        imgbase64,
                        chat_history
                    )
                    v_ms = int((time.perf_counter() - v_t0) * 1000)
                    del imgbase64
                    
                    yield {
                        "_activity": {
                            "event": "vision_processing",
                            "status": "done",
                            "elapsed_ms": v_ms
                        }
                    }
                    
                    self.sessions[session_id][-1].content = vision_res
                    yield vision_res
                    self.save_chat_session(session_id)
                    return
                    
                except Exception as e:
                    import logging
                    log = logging.getLogger("J.A.R.V.I.S")
                    log.error(f"[ChatService] Screen capture fallback failed: {e}")
                    no_img_msg = "Please open the webcam or attach an image so I can see what you're referring to."
                    self.sessions[session_id][-1].content = no_img_msg
                    yield no_img_msg
                    self.save_chat_session(session_id)
                    return
        
        if query_type in ("task", "automation", "mixed") and tasks:
            if self.task_manager and self.brain_service:
                # Extract actual intent and payload for each task
                # Use clean_user_message (without cam bypass token)
                intents = self.brain_service.extract_task_payloads(clean_user_message, tasks, chat_history)
                
                yield {
                    "_activity": {
                        "event": "task_detected", 
                        "tasks": tasks
                    }
                }

                # Separate heavy (background) and instant (direct) tasks
                heavy_intents = [i for i in intents if i[0] in HEAVY_INTENTS]
                instant_intents = [i for i in intents if i[0] in INSTANT_INTENTS]

                # 1. Handle Heavy Tasks (Background)
                for intent_type, payload in heavy_intents:
                    t_id = self.task_manager.submit_task(
                        intent_type=intent_type, 
                        payload=payload,
                        session_id=session_id,
                        chat_history=chat_history
                    )
                    
                    yield {
                        "_activity": {
                            "event": "task_submitted", 
                            "task_id": t_id, 
                            "type": intent_type
                        }
                    }
                
                if heavy_intents:
                    yield {
                        "background_tasks": self.task_manager.get_session_tasks(session_id)
                    }

                # 2. Handle Instant Tasks (Direct)
                if instant_intents and self.task_executor:
                    task_res = self.task_executor.execute(instant_intents, chat_history)
                    
                    # Yield direct results (wopens, plays, etc.) wrapped in actions
                    yield {
                        "actions": {
                            "wopens": task_res.wopens,
                            "plays": task_res.plays,
                            "googlesearches": task_res.googlesearches,
                            "youtubesearches": task_res.youtubesearches,
                            "images": task_res.images,
                            "contents": task_res.contents,
                            "cam": task_res.cam,
                        }
                    }

                    # If this was PURELY an instant task (not mixed), use the conversational response
                    if query_type == "task" and task_res.text:
                        self.sessions[session_id][-1].content = task_res.text
                        yield task_res.text
                        self.save_chat_session(session_id)
                        return
                        
                # 3. If there were ONLY background tasks, return instantly
                if not instant_intents and heavy_intents and query_type == "task":
                    msg = "I've started that task in the background for you."
                    self.sessions[session_id][-1].content = msg
                    yield msg
                    self.save_chat_session(session_id)
                    return

        yield {
            "_activity": {
                "event": "streaming_started", 
                "route": query_type
            }
        }

        chunk_count = 0
        t0 = time.perf_counter()

        try:
            if query_type == "general":
                stream = self.groq_service.stream_response(
                    question=clean_user_message, 
                    chat_history=chat_history, 
                    key_start_index=chat_idx
                )

            else:
                stream = self.groq_service.stream_response_with_prefetched(
                    question=clean_user_message,
                    chat_history=chat_history,
                    formatted_results=formatted_results,
                    payload=search_payload,
                    key_start_index=chat_idx,
                )

            for chunk in stream:
                if isinstance(chunk, dict):
                    yield chunk
                    continue

                if chunk_count == 0:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    yield {
                        "_activity": {
                            "event": "first_chunk", 
                            "route": query_type, 
                            "elapsed_ms": elapsed_ms
                        }
                    }

                self.sessions[session_id][-1].content += chunk
                chunk_count += 1

                if chunk_count % SAVE_EVERY_N_CHUNKS == 0:
                    self.save_chat_session(session_id, log_timing=False)

                yield chunk

        except Exception as e:
            logger.error("[JARVIS-STREAM] Exception during stream: %s", e, exc_info=True)
            error_msg = f"\n\n[System: I encountered an error while processing that: {str(e)}]"
            self.sessions[session_id][-1].content += error_msg
            yield error_msg

        finally:
            final_response = self.sessions[session_id][-1].content
            logger.info(
                "[JARVIS-STREAM] Completed | Route: %s | Chunks: %d | Response length: %d chars",
                query_type, 
                chunk_count, 
                len(final_response)
            )
            self.save_chat_session(session_id)
            self.update_vector_store_live(session_id)

    def save_chat_session(self, session_id: str, log_timing: bool = True):
        if session_id not in self.sessions or not self.sessions[session_id]:
            return

        messages = self.sessions[session_id]
        safe_session_id = session_id.replace("-", "").replace(".", "_")
        filename = f"chat_{safe_session_id}.json"
        filepath = CHATS_DATA_DIR / filename

        chat_dict = {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role, 
                    "content": msg.content
                } 
                for msg in messages
            ]
        }

        max_retries = 3
        last_exc = None

        for attempt in range(max_retries):
            try:
                with self._save_lock:
                    t0 = time.perf_counter() if log_timing else 0

                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(
                            chat_dict, 
                            f, 
                            indent=2, 
                            ensure_ascii=False
                        )

                    if log_timing:
                        logger.info(
                            "[TIMING] save_session_json: %.3fs", 
                            time.perf_counter() - t0
                        )

                return

            except OSError as e:
                last_exc = e
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))

            except Exception as e:
                logger.error(
                    "Failed to save chat session %s to disk: %s", 
                    session_id, 
                    e
                )
                return

        logger.error(
            "Failed to save chat session %s after %d retries: %s", 
            session_id, 
            max_retries, 
            last_exc
        )