import json
import logging
import time
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import List, Optional, Dict, Iterator, Any, Union
import uuid
import threading
from threading import Thread, Lock

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
        memory_service = None,
    ):
        self.groq_service = groq_service
        self.brain_service = brain_service
        self.task_executor = task_executor
        self.vision_service = vision_service
        self.task_manager = task_manager
        self.orchestrator = orchestrator
        self.memory_service = memory_service
        self._state_mgr = None
        self.sessions: Dict[str, List[ChatMessage]] = {}
        self.pending_memory_updates = {}
        self.pending_actions = {}
        self.current_preset = 'default'
        self.session_presets: Dict[str, str] = {}
        self.last_metrics: Dict[str, Dict[str, int]] = {}
        self._save_lock = Lock()

    def set_preset(self, preset_name: str, session_id: str = None):
        if session_id:
            self.session_presets[session_id] = preset_name
        else:
            self.current_preset = preset_name

    def _apply_preset_to_question(self, session_id: str, question: str) -> str:
        preset = self.session_presets.get(session_id, self.current_preset)
        if preset != 'default':
            from config import PRESETS
            addition = PRESETS.get(preset)
            if addition:
                return f"[SYSTEM MODE: {preset.upper()} - {addition}]\n\n{question}"
        return question


    def _detect_remember_forget(self, message: str) -> Optional[tuple]:
        msg_lower = message.lower().strip()
        if msg_lower.startswith("remember that "):
            return ("remember", message[14:].strip())
        elif msg_lower.startswith("remember: "):
            return ("remember", message[10:].strip())
        elif msg_lower.startswith("note that "):
            return ("remember", message[10:].strip())
        elif msg_lower in ("forget all", "clear memory"):
            return ("forget_all", None)
        elif msg_lower.startswith("forget "):
            return ("forget", message[7:].strip())
        elif msg_lower.startswith("delete memory "):
            return ("forget", message[14:].strip())
        return None

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
            self.session_presets[new_session_id] = 'default'
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
            self.session_presets[session_id] = 'default'
            logger.info(
                "[TIMING] session_get_or_create: %.3fs (disk)", 
                time.perf_counter() - t0
            )
            return session_id

        self.sessions[session_id] = []
        self.session_presets[session_id] = 'default'
        logger.info(
            "[TIMING] session_get_or_create: %.3fs (new_id)", 
            time.perf_counter() - t0
        )
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
            
        if len(self.sessions[session_id]) == 0 and role == "user" and self.memory_service:
            self.memory_service.check_usage_patterns(self.groq_service)
            relevant_memories = self.memory_service.get_todays_relevant_memories()
            if relevant_memories:
                facts = "\n".join(relevant_memories)
                context_msg = f"{facts}\nIf natural, you may bring this up conversationally, but only if it fits — do not force it into every response."
                self.sessions[session_id].append(ChatMessage(role="system", content=context_msg))
        
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
        self.last_metrics[session_id] = {}
        logger.info("[GENERAL-JARVIS] Session: %s | User: %.200s", session_id[:12], user_message)
        
        # Route through unified JARVIS brain stream so tasks, actions, and WebSocket commands execute!
        response_parts = []
        for chunk in self.process_jarvis_message_stream(session_id, user_message):
            if isinstance(chunk, str):
                response_parts.append(chunk)
            elif isinstance(chunk, dict) and "text" in chunk:
                response_parts.append(chunk["text"])

        response = "".join(response_parts).strip()
        if not response and session_id in self.sessions and self.sessions[session_id]:
            response = self.sessions[session_id][-1].content or "Task executed, Boss."

        return response or "Task executed, Boss."

    def process_realtime_message(self, session_id: str, user_message: str) -> str:

        logger.info(
            "[REALTIME] Session: %s | User: %.200s", 
            session_id[:12], 
            user_message
        )
        
        self.add_message(session_id, "user", user_message)

        chat_history = self.format_history_for_llm(session_id, exclude_last=True)
        mem_prefix = ""
        if self.memory_service:
            recent = [str(m.content) for m in self.sessions.get(session_id, [])[:-2][-3:]]
            mem_prefix = self.memory_service.build_memory_context(session_id, user_message, recent)
        enriched_question = f"{mem_prefix}\n{user_message}".strip() if mem_prefix else user_message
        enriched_question = self._apply_preset_to_question(session_id, enriched_question)
        
        logger.info(
            "[REALTIME] History pairs sent to LLM: %d", 
            len(chat_history)
        )

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        
        response = self.groq_service.get_response(
            question=enriched_question, 
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
        if self.memory_service:
            _snapshot = list(self.sessions[session_id])
            def _run_summarise():
                summary = self.memory_service.maybe_summarise(session_id, _snapshot, self.groq_service)
                if summary:
                    with self._save_lock:
                        if len(self.sessions[session_id]) > 6:
                            summary_msg = ChatMessage(role="system", content=f"Previous Context Summary:\n{summary}")
                            self.sessions[session_id] = [summary_msg] + self.sessions[session_id][-6:]
                            self.save_chat_session(session_id, log_timing=False)
            Thread(target=_run_summarise).start()
        return response

    def _yield_context_usage(self, chat_history: List[tuple], enriched_question: str) -> Dict:
        try:
            total_chars = sum(len(str(m[0])) + len(str(m[1])) for m in chat_history) + len(enriched_question)
            approx_tokens = total_chars // 4
            percentage = min(100, int((approx_tokens / 8192) * 100))
            return {
                "_activity": {
                    "event": "context_usage",
                    "percentage": percentage
                }
            }
        except Exception:
            return {}

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
        mem_prefix = ""
        if self.memory_service:
            recent = [str(m.content) for m in self.sessions.get(session_id, [])[-4:-1]]
            mem_prefix = self.memory_service.build_memory_context(session_id, user_message, recent)
        enriched_question = f"{mem_prefix}\n{user_message}".strip() if mem_prefix else user_message
        enriched_question = self._apply_preset_to_question(session_id, enriched_question)
        
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
        
        context_usage = self._yield_context_usage(chat_history, enriched_question)
        if context_usage:
            yield context_usage

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        chunk_count = 0
        t0 = time.perf_counter()

        try:
            for chunk in self.groq_service.stream_response(
                question=enriched_question, 
                chat_history=chat_history, 
                key_start_index=chat_idx,
                raw_message=user_message
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
            if self.memory_service:
                _snapshot = list(self.sessions[session_id])
                def _run_summarise():
                    summary = self.memory_service.maybe_summarise(session_id, _snapshot, self.groq_service)
                    if summary:
                        with self._save_lock:
                            if len(self.sessions[session_id]) > 6:
                                new_msgs = self.sessions[session_id][-6:]
                                for m in new_msgs:
                                    if m.role == "user":
                                        m.content = f"[Previous Context Summary]\n{summary}\n\n[End Summary]\n{m.content}"
                                        break
                                self.sessions[session_id] = new_msgs
                                self.save_chat_session(session_id, log_timing=False)
                Thread(target=_run_summarise).start()

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
        mem_prefix = ""
        if self.memory_service:
            recent = [str(m.content) for m in self.sessions.get(session_id, [])[-4:-1]]
            mem_prefix = self.memory_service.build_memory_context(session_id, user_message, recent)
        enriched_question = f"{mem_prefix}\n{user_message}".strip() if mem_prefix else user_message
        enriched_question = self._apply_preset_to_question(session_id, enriched_question)
        
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
        
        context_usage = self._yield_context_usage(chat_history, enriched_question)
        if context_usage:
            yield context_usage

        _, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=False)
        chunk_count = 0
        t0 = time.perf_counter()

        try:
            for chunk in self.groq_service.stream_response(
                question=enriched_question, 
                chat_history=chat_history, 
                key_start_index=chat_idx,
                use_search=True,
                raw_message=user_message
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
            if self.memory_service:
                _snapshot = list(self.sessions[session_id])
                def _run_summarise():
                    summary = self.memory_service.maybe_summarise(session_id, _snapshot, self.groq_service)
                    if summary:
                        with self._save_lock:
                            if len(self.sessions[session_id]) > 6:
                                summary_msg = ChatMessage(role="system", content=f"Previous Context Summary:\n{summary}")
                                self.sessions[session_id] = [summary_msg] + self.sessions[session_id][-6:]
                                self.save_chat_session(session_id, log_timing=False)
                Thread(target=_run_summarise).start()

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
        
        msg_lower = clean_user_message.lower().strip()
        prefix = ""
        
        # 1. Handle pending memory updates (Contradictions)
        if session_id in self.pending_memory_updates:
            pending = self.pending_memory_updates.pop(session_id)
            if msg_lower in ("yes", "y", "yeah", "update", "do it", "sure"):
                try:
                    res = self.memory_service.store_knowledge(
                        pending['content'], 
                        self.brain_service.groq_service, 
                        force_update_id=pending['id'], 
                        force_category=pending['category']
                    )
                    yield f"Done. {res}"
                except Exception as e:
                    yield f"Failed to update memory: {e}"
                return
            else:
                prefix = "Okay, I've discarded the new fact and kept the old memory.\n\n"
                
        # 2. Handle pending irreversible actions
        elif session_id in self.pending_actions:
            pending_action = self.pending_actions.pop(session_id)
            if msg_lower in ("yes", "y", "yeah", "do it", "sure", "confirm"):
                from app.services.action_broker import ActionBroker
                res = ActionBroker.dispatch(pending_action['tool'], pending_action['args'], confirmed=True)
                yield f"Action completed: {res}"
                return
            else:
                prefix = "Action cancelled.\n\n"
                
        if prefix:
            yield prefix
        
        if self.memory_service:
            mem_cmd = self._detect_remember_forget(clean_user_message)
            if mem_cmd:
                action, payload = mem_cmd
                if action == "remember":
                    # Use brain_service.groq_service (Llama 3) for lightning-fast memory categorization instead of multi-tier router
                    res = self.memory_service.store_knowledge(payload, self.brain_service.groq_service)
                    if res.startswith("__CONTRADICT__:"):
                        parts = res.split("::", 1)
                        header = parts[0]
                        explanation = parts[1] if len(parts) > 1 else "Unknown contradiction"
                        _, match_id, cat, content = header.split(":", 3)
                        
                        self.pending_memory_updates[session_id] = {
                            "id": int(match_id),
                            "category": cat,
                            "content": content
                        }
                        yield f"This conflicts with what I remember: {explanation}. Should I update it?"
                    else:
                        yield f"Noted, Boss. {res}"
                elif action == "forget":
                    res = self.memory_service.forget_knowledge(payload)
                    yield f"Done, Boss. {res}"
                elif action == "forget_all":
                    res = self.memory_service.forget_all()
                    yield f"Done, Boss. {res}"
                return
            else:
                # Trigger passive fact extraction in background
                Thread(
                    target=self.memory_service.extract_passive_knowledge, 
                    args=(clean_user_message, self.brain_service.groq_service)
                ).start()
        
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
        memory_ctx = ""
        if self.memory_service:
            memory_ctx = self.memory_service.build_memory_context(session_id, clean_user_message)
        
        # Build enriched question with screen/memory context prepended inline
        ctx_prefix_parts = []
        if screen_ctx:
            ctx_prefix_parts.append(screen_ctx)
        if memory_ctx:
            ctx_prefix_parts.append(memory_ctx)
        enriched_jarvis_question = ("\n".join(ctx_prefix_parts) + "\n" + clean_user_message).strip() if ctx_prefix_parts else clean_user_message
        enriched_jarvis_question = self._apply_preset_to_question(session_id, enriched_jarvis_question)
        if ctx_prefix_parts:
            logger.info("[CONTEXT] Injected screen/memory context into question (%d chars)", len("\n".join(ctx_prefix_parts)))

        yield {
            "_activity": {
                "event": "query_detected", 
                "message": clean_user_message
            }
        }

        brain_idx, chat_idx = get_next_key_pair(len(GROQ_API_KEYS), need_brain=True)

        # File Delivery Pre-Check
        import re
        FILE_DELIVERY_PATTERNS = [
            r"send (?:me |the )?(.*\.(?:pdf|docx|xlsx|zip|png|jpg))",
            r"(?:download|forward|share|get) (?:the )?(pdf|file|attachment|document)",
            r"(pdf|file|document) (?:from|in) (?:gmail|email|mail|downloads|desktop)",
            r"(?:send|find).*(pdf|file|document).*telegram"
        ]
        
        file_query = None
        for pattern in FILE_DELIVERY_PATTERNS:
            match = re.search(pattern, clean_user_message, re.IGNORECASE)
            if match:
                file_query = match.group(1)
                break
                
        if file_query:
            if file_query.lower() in ["file", "attachment", "document"]:
                file_query = "pdf" # Default to pdf if they just ask for "the file"
            yield "Sending it to your Telegram now, Boss."
            
            try:
                from app.telegram_bot import background_sendfile
                Thread(target=background_sendfile, args=(file_query,)).start()
            except Exception as e:
                logger.error(f"Failed to start background sendfile thread: {e}")
                
            yield {"actions": {"sendfile": file_query}}
            return
            
        query_type = "realtime"
        reasoning = "Defaulting to realtime"
        brain_elapsed_ms = 0
        formatted_results = ""
        search_payload = None

        def _run_brain():
            if self.orchestrator:
                return self.orchestrator.route_request(clean_user_message, chat_history, llm_router=self.groq_service)
            if self.brain_service and brain_idx is not None:
                qt, tasks, r, ms, intent_dict = self.brain_service.classify(
                    clean_user_message, 
                    chat_history, 
                    key_index=brain_idx
                )
                return {"category": qt, "task_types": tasks, "method": r, "elapsed_ms": ms, "intent_dict": intent_dict}
            return {"category": "realtime", "task_types": [], "method": "No brain service", "elapsed_ms": 0, "intent_dict": {}}

        def _run_search():
            return self.groq_service.prefetch_web_search(
                clean_user_message, 
                chat_history
            )

        executor = ThreadPoolExecutor(max_workers=2)
        try:
            future_brain = executor.submit(_run_brain)
            future_search = executor.submit(_run_search)

            try:
                brain_res = future_brain.result(timeout=JARVIS_BRAIN_SEARCH_TIMEOUT)
                
                if brain_res.get("intercepted"):
                    yield {"text": brain_res["result"]}
                    return
                    
                query_type = brain_res.get("category", "realtime")
                tasks = brain_res.get("task_types", [])
                reasoning = brain_res.get("method", "")
                brain_elapsed_ms = brain_res.get("elapsed_ms", 0)
                intent_dict = brain_res.get("intent_dict", {})

            except FuturesTimeoutError:
                logger.warning(
                    "[JARVIS] Brain classification timed out after %ds, defaulting to realtime", 
                    JARVIS_BRAIN_SEARCH_TIMEOUT
                )
                query_type, tasks, reasoning, brain_elapsed_ms, intent_dict = (
                    "realtime", [], "Brain timeout, defaulting to realtime", 0, {}
                )

            if query_type in ("general", "casual_chat"):
                formatted_results, search_payload = "", None
                # We do not wait for future_search here.

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
        finally:
            executor.shutdown(wait=False)

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
                # User requested vision but no direct image provided -> try laptop screen capture
                imgbase64_captured = None
                from config import IS_CLOUD
                if IS_CLOUD:
                    from app.websocket_manager import laptop_manager
                    if laptop_manager.is_connected():
                        logger.info("[VISION] Requesting screen capture from laptop via WebSocket")
                        resp = laptop_manager.send_and_wait(action="capture_screen", timeout=5)
                        if resp.get("status") == "success" and resp.get("image_b64"):
                            imgbase64_captured = resp.get("image_b64")

                if not imgbase64_captured and not IS_CLOUD:
                    try:
                        from jarvis_os.observers.screen_observer import ScreenObserver
                        observer = ScreenObserver()
                        image_bytes = observer.capture_screen()
                        imgbase64_captured = observer.sanitize_data(image_bytes)
                        del image_bytes
                    except Exception as e:
                        logger.warning(f"[VISION] Local screen capture failed: {e}")

                if imgbase64_captured and self.vision_service:
                    try:
                        v_t0 = time.perf_counter()
                        vision_res = self.vision_service.analyze_image(
                            clean_user_message,
                            imgbase64_captured,
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
                    except Exception as e:
                        logger.warning(f"[VISION] Image analysis failed: {e}")

                # If vision capture failed/unavailable, fall through to normal LLM chat below
                logger.info("[VISION] Vision capture unavailable, falling back to standard LLM response")
                query_type = "general"
        
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
                            "desktop_apps": task_res.desktop_apps,
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
                    elif query_type == "mixed" and task_res.text:
                        # For mixed queries, append the task result so the LLM can use it
                        formatted_results = formatted_results + f"\n\n[Task Result: {task_res.text}]\n" if formatted_results else f"[Task Result: {task_res.text}]\n"
                        
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
            from app.tools.registry import ToolRegistry
            relevant_tools = list(ToolRegistry.get_relevant_tools(enriched_jarvis_question, top_k=5).values())
            tools_str = "\nAvailable Tools (You can instruct the user to run them if needed):\n" + "\n".join([f"- {t.name}: {t.description}" for t in relevant_tools]) if relevant_tools else ""
            
            query_type_clean = str(query_type).lower().strip()
            if query_type_clean in ("general", "casual_chat", "realtime"):
                question_to_send = enriched_jarvis_question
                if query_type_clean == "casual_chat":
                    question_to_send = f"[CASUAL MODE] This is casual conversation, not a work task. Respond more like texting a friend — shorter, relaxed, occasional humor where it fits. No need to over-explain or offer additional help unless asked.\n\n{question_to_send}"
                    
                stream = self.groq_service.stream_response(
                    question=question_to_send, 
                    chat_history=chat_history, 
                    key_start_index=chat_idx,
                    tools_str=tools_str,
                    intent_dict=intent_dict,
                    raw_message=clean_user_message
                )

            else:
                stream = self.groq_service.stream_response_with_prefetched(
                    question=enriched_jarvis_question,
                    chat_history=chat_history,
                    formatted_results=formatted_results,
                    payload=search_payload,
                    key_start_index=chat_idx,
                    tools_str=tools_str,
                    intent_dict=intent_dict,
                    raw_message=clean_user_message
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
            if chunk_count == 0:
                yield {
                    "_activity": {
                        "event": "first_chunk", 
                        "route": query_type, 
                        "elapsed_ms": int((time.perf_counter() - t0) * 1000)
                    }
                }
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
            if self.memory_service:
                _snapshot = list(self.sessions[session_id])
                Thread(
                    target=self.memory_service.maybe_summarise, 
                    args=(session_id, _snapshot, self.groq_service)
                ).start()

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