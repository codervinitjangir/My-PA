from typing import List, Optional, Iterator, Tuple, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
import logging
import time
import os
from tavily import TavilyClient

from app.providers.base_provider import BaseProvider
from app.services.vector_store import VectorStoreService
from app.utils.time_info import get_time_information
from app.utils.retry import with_retry
from config import (
    GROQ_API_KEYS,
    GROQ_MODEL,
    INTENT_CLASSIFY_MODEL,
    JARVIS_SYSTEM_PROMPT,
    GENERAL_CHAT_ADDENDUM,
    REALTIME_CHAT_ADDENDUM
)

logger = logging.getLogger("J.A.R.V.I.S")
GROQ_REQUEST_TIMEOUT = 60
GROQ_REQUEST_TIMEOUT_FAST = 15

ALL_APIS_FAILED_MESSAGE = (
    "I'm unable to process your request at the moment. All API services are "
    "temporarily unavailable. Please try again in a few minutes."
)

QUERY_EXTRACTION_PROMPT = (
    "You are a search query optimizer. Convert the user's message into a clean, focused "
    "web search query (max 10 words). Rules:\n"
    "- Remove filler words (you know, like, something, can you, tell me, search)\n"
    "- Add specifics: dates (today, 2026), event names, full names\n"
    "- For sports: include league name, team names, 'live score today'\n"
    "- For people: include full name + what user wants to know\n"
    "- Resolve references (him, that, it) from conversation history\n"
    "Output ONLY the search query. Nothing else."
)

class AllGroqApisFailedError(Exception):
    pass

def escape_curly_braces(text: str) -> str:
    if not text:
        return text
    return text.replace("{", "{{").replace("}", "}}")

REPEAT_WINDOW = 100
REPEAT_THRESHOLD = 3
REPEAT_CHECK_INTERVAL = 200

def _detect_repetition_loop(text: str) -> bool:
    if len(text) < REPEAT_WINDOW * REPEAT_THRESHOLD:
        return False
    phrase = text[-REPEAT_WINDOW:]
    return text.count(phrase) >= REPEAT_THRESHOLD

def _truncate_at_repetition(text: str) -> str:
    if len(text) < REPEAT_WINDOW * REPEAT_THRESHOLD:
        return text
    phrase = text[-REPEAT_WINDOW:]
    if text.count(phrase) < REPEAT_THRESHOLD:
        return text
    first = text.find(phrase)
    second = text.find(phrase, first + 1)
    if second > first:
        return text[:second].rstrip()
    return text

def is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "429" in str(exc) or "rate limit" in msg or "tokens per day" in msg

def _log_timing(label: str, elapsed: float, extra: str = ""):
    msg = f"[{label}] {elapsed:.3f}s"
    if extra:
        msg += f" ({extra})"
    logger.info(msg)

def mask_api_key(key: str) -> str:
    if not key or len(key) <= 12:
        return "***masked***"
    return f"{key[:8]}...{key[-4:]}"

class GroqProvider(BaseProvider):
    def __init__(self, vector_store_service: VectorStoreService):
        if not GROQ_API_KEYS:
            raise ValueError("No Groq API keys configured. Set GROQ_API_KEY in .env")
            
        self.llms = [
            ChatGroq(
                groq_api_key=key,
                model_name=GROQ_MODEL,
                temperature=0.5,
                max_tokens=1024,
                request_timeout=GROQ_REQUEST_TIMEOUT,
                model_kwargs={"frequency_penalty": 0.3},
            )
            for key in GROQ_API_KEYS
        ]
        
        self.vector_store_service = vector_store_service
        logger.info(f"Initialized GroqService with {len(GROQ_API_KEYS)} API key(s)")

        # Realtime search components
        tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        if tavily_api_key:
            self.tavily_client = TavilyClient(api_key=tavily_api_key)
            logger.info("Tavily search client initialized successfully in GroqService")
        else:
            self.tavily_client = None
            logger.warning("TAVILY_API_KEY not set. Realtime search will be unavailable.")
            
        if GROQ_API_KEYS:
            self._fast_llm = ChatGroq(
                groq_api_key=GROQ_API_KEYS[0],
                model_name=INTENT_CLASSIFY_MODEL,
                temperature=0.0,
                request_timeout=GROQ_REQUEST_TIMEOUT_FAST,
                max_tokens=50,
            )
        else:
            self._fast_llm = None

    def _extract_search_query(self, question: str, chat_history: Optional[List[tuple]] = None) -> str:
        if not self._fast_llm:
            return question
            
        q = question.strip()
        q_lower = q.lower()
        has_filler = any(p in q_lower for p in [
            " it ", " that ", " him ", " her ", " then ", " you know ",
            " something ", " like ", " going on ", " can you ", " tell me ",
            " search ", " right now ", " please ",
        ])
        
        if len(q) <= 30 and not has_filler:
            return q
            
        try:
            t0 = time.perf_counter()
            history_context = ""
            if chat_history:
                recent = chat_history[-3:]
                parts = []
                for h, a in recent:
                    parts.append(f"User: {h[:200]}")
                    parts.append(f"Assistant: {a[:200]}")
                history_context = "\n".join(parts)
                
            if history_context:
                full_prompt = (
                    f"{QUERY_EXTRACTION_PROMPT}\n\n"
                    f"Recent conversation:\n{history_context}\n\n"
                    f"User's latest message: {question}\n\n"
                    "Search query:"
                )
            else:
                full_prompt = (
                    f"{QUERY_EXTRACTION_PROMPT}\n\n"
                    f"User's message: {question}\n\n"
                    "Search query:"
                )
                
            response = self._fast_llm.invoke(full_prompt)
            extracted = response.content.strip().strip('"').strip("'")
            
            if extracted and 3 <= len(extracted) <= 200:
                logger.info("[SEARCH] Query extraction: '%s' -> '%s' (%.3fs)", question[:80], extracted[:80], time.perf_counter() - t0)
                return extracted
            return question
        except Exception as e:
            logger.warning("[SEARCH] Query extraction failed (%s)", e)
            return question

    def search_tavily(self, query: str, num_results: int = 5) -> Tuple[str, Optional[dict]]:
        if not self.tavily_client:
            return ("", None)
        if not query or not str(query).strip():
            return ("", None)
            
        try:
            t0 = time.perf_counter()
            response = with_retry(
                lambda: self.tavily_client.search(
                    query=query,
                    search_depth="fast",
                    max_results=num_results,
                    include_answer=True,
                    include_raw_content=False,
                ),
                max_retries=3,
                initial_delay=1.0,
            )
            
            results = response.get("results", [])
            ai_answer = response.get("answer", "")
            
            if not results and not ai_answer:
                return ("", None)
                
            payload: Optional[dict] = {
                "query": query,
                "answer": ai_answer,
                "results": [
                    {
                        "title": r.get("title", "No title"),
                        "content": (r.get("content") or "")[:300],
                        "url": r.get("url", ""),
                        "score": round(float(r.get("score", 0)), 2),
                    }
                    for r in results[:num_results]
                ]
            }
            
            parts = [f"--- WEB SEARCH RESULTS FOR: {query} ---\n"]
            if ai_answer:
                parts.append(f"AI-SYNTHESIZED ANSWER (use this as your primary source):\n{ai_answer}\n")
            if results:
                parts.append("INDIVIDUAL SOURCES:")
                for i, result in enumerate(results[:num_results], 1):
                    title = result.get("title", "No Title")
                    content = result.get("content", "")
                    url = result.get("url", "")
                    score = result.get("score", 0)
                    parts.append(f"\n[Source {i}] (relevance: {score:.2f})")
                    parts.append(f"Title: {title}")
                    if content:
                        parts.append(f"Content: {content}")
                    if url:
                        parts.append(f"URL: {url}")
            parts.append("\n--- END SEARCH RESULTS ---")
            formatted = "\n".join(parts)
            logger.info("[TAVILY] %d results, AI answer: %s (%.3fs)", len(results), "Yes" if ai_answer else "No", time.perf_counter() - t0)
            return (formatted, payload)
        except Exception as e:
            logger.error("Error performing Tavily search: %s", e)
            return ("", None)

    def prefetch_web_search(self, question: str, chat_history: Optional[List[tuple]] = None) -> Tuple[str, Optional[dict]]:
        try:
            search_query = self._extract_search_query(question, chat_history)
            formatted_results, payload = self.search_tavily(search_query, num_results=5)
            return (formatted_results or "", payload)
        except Exception as e:
            logger.warning("[SEARCH] Pre-fetch failed: %s", e)
            return ("", None)

    def _invoke_llm(self, prompt: ChatPromptTemplate, messages: list, question: str, key_start_index: int = 0) -> str:
        n = len(self.llms)
        last_exc = None
        for j in range(n):
            i = (key_start_index + j) % n
            try:
                chain = prompt | self.llms[i]
                response = with_retry(lambda: chain.invoke({"history": messages, "question": question}), max_retries=2, initial_delay=0.5)
                text = response.content
                if _detect_repetition_loop(text):
                    text = _truncate_at_repetition(text)
                return text
            except Exception as e:
                last_exc = e
                if j < n - 1:
                    continue
                break
        raise AllGroqApisFailedError(ALL_APIS_FAILED_MESSAGE) from last_exc

    def _stream_llm(self, prompt: ChatPromptTemplate, messages: list, question: str, key_start_index: int = 0) -> Iterator[str]:
        n = len(self.llms)
        last_exc = None
        for j in range(n):
            i = (key_start_index + j) % n
            try:
                chain = prompt | self.llms[i]
                accumulated = ""
                last_check_len = 0
                for chunk in chain.stream({"history": messages, "question": question}):
                    content = ""
                    if hasattr(chunk, "content"):
                        content = chunk.content or ""
                    elif isinstance(chunk, dict) and "content" in chunk:
                        content = chunk.get("content", "") or ""
                    if isinstance(content, str) and content:
                        accumulated += content
                        if len(accumulated) - last_check_len >= REPEAT_CHECK_INTERVAL:
                            last_check_len = len(accumulated)
                            if _detect_repetition_loop(accumulated):
                                break
                        yield content
                return
            except Exception as e:
                last_exc = e
                if j < n - 1:
                    continue
                break
        raise AllGroqApisFailedError(ALL_APIS_FAILED_MESSAGE) from last_exc

    def _build_prompt_and_messages(self, question: str, chat_history: Optional[List[tuple]] = None, extra_system_parts: Optional[List[str]] = None, mode_addendum: str = "") -> tuple:
        import os
        if os.getenv("ENABLE_JARVIS_OS", "false").lower() == "true":
            try:
                from jarvis_os.runtime.runtime_manager import RuntimeManager
                jarvis_context = RuntimeManager().build_ai_context()
                if jarvis_context:
                    extra_system_parts = extra_system_parts or []
                    extra_system_parts.append(jarvis_context)
            except Exception:
                pass

        context = ""
        try:
            retriever = self.vector_store_service.get_retriever(k=5)
            context_docs = retriever.invoke(question)
            if context_docs:
                context = "\n".join([doc.page_content for doc in context_docs])
        except Exception:
            pass

        time_info = get_time_information()
        system_message = JARVIS_SYSTEM_PROMPT + f"\n\nCurrent time and date: {time_info}"
        
        if context:
            system_message += f"\n\nRelevant context from your learning data and past conversations:\n{escape_curly_braces(context)}"
        if extra_system_parts:
            system_message += "\n\n" + "\n\n".join(extra_system_parts)
        if mode_addendum:
            system_message += f"\n\n{mode_addendum}"
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])
        
        messages = []
        if chat_history:
            for human_msg, ai_msg in chat_history:
                messages.append(HumanMessage(content=human_msg))
                messages.append(AIMessage(content=ai_msg))
                
        return prompt, messages

    def get_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> str:
        try:
            extra_parts = None
            mode_addendum = GENERAL_CHAT_ADDENDUM
            
            if use_search:
                mode_addendum = REALTIME_CHAT_ADDENDUM
                search_query = self._extract_search_query(question, chat_history)
                formatted_results, _ = self.search_tavily(search_query, num_results=5)
                if formatted_results:
                    extra_parts = [escape_curly_braces(formatted_results)]
            
            prompt, messages = self._build_prompt_and_messages(question, chat_history, extra_system_parts=extra_parts, mode_addendum=mode_addendum)
            return self._invoke_llm(prompt, messages, question, key_start_index=key_start_index)
        except Exception as e:
            raise Exception(f"Error getting response from Groq: {str(e)}") from e

    def stream_response(self, question: str, chat_history: Optional[List[tuple]] = None, key_start_index: int = 0, use_search: bool = False) -> Iterator[Any]:
        try:
            extra_parts = None
            mode_addendum = GENERAL_CHAT_ADDENDUM
            
            if use_search:
                mode_addendum = REALTIME_CHAT_ADDENDUM
                yield {"activity": {"event": "extracting_query", "message": "Extracting search query..."}}
                search_query = self._extract_search_query(question, chat_history)
                yield {"activity": {"event": "searching_web", "query": search_query, "message": f"Searching web for: {search_query}"}}
                
                formatted_results, payload = self.search_tavily(search_query, num_results=5)
                if formatted_results:
                    num_results = len(payload.get("results", [])) if payload else 0
                    yield {"activity": {"event": "search_completed", "message": f"Search completed: {num_results} results"}}
                    extra_parts = [escape_curly_braces(formatted_results)]
                else:
                    yield {"activity": {"event": "search_completed", "message": "No search results found"}}
                if payload:
                    yield {"search_results": payload}
            else:
                yield {"activity": {"event": "context_retrieved", "message": "Retrieved relevant context from knowledge base"}}

            prompt, messages = self._build_prompt_and_messages(question, chat_history, extra_system_parts=extra_parts, mode_addendum=mode_addendum)
            yield from self._stream_llm(prompt, messages, question, key_start_index=key_start_index)
        except Exception as e:
            raise Exception(f"Error streaming response from Groq: {str(e)}") from e

    def stream_response_with_prefetched(self, question: str, chat_history: Optional[List[tuple]] = None, formatted_results: Optional[str] = None, payload: Optional[dict] = None, key_start_index: int = 0) -> Iterator[Any]:
        try:
            extra_parts = [escape_curly_braces(formatted_results)] if formatted_results else None
            prompt, messages = self._build_prompt_and_messages(question, chat_history, extra_system_parts=extra_parts, mode_addendum=REALTIME_CHAT_ADDENDUM)
            yield from self._stream_llm(prompt, messages, question, key_start_index=key_start_index)
        except Exception as e:
            raise Exception(f"Error in streaming response with prefetched: {str(e)}") from e