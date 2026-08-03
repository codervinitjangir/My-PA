"""
Gemini 2.0 Flash Provider — Tier 1 LLM for J.A.R.V.I.S.

Uses the current google-genai SDK (google.genai — NOT the deprecated google.generativeai).
Reads GEMINI_API_KEY from env. Mirrors the GroqProvider interface so it can be swapped in
transparently via LLMRouter.
"""
import logging
import time
from typing import List, Optional, Iterator, Tuple, Any

from app.providers.base_provider import BaseProvider
from app.services.vector_store import VectorStoreService
from app.utils.time_info import get_time_information
from config import (
    GEMINI_API_KEYS,
    JARVIS_SYSTEM_PROMPT,
    GENERAL_CHAT_ADDENDUM,
    REALTIME_CHAT_ADDENDUM,
)

logger = logging.getLogger("J.A.R.V.I.S")

_GEMINI_AVAILABLE = False
_genai_client_cls = None   # google.genai.Client class

try:
    from google import genai as _google_genai
    from google.genai import types as _genai_types
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
    _genai_client_cls = _google_genai.Client
    _GEMINI_AVAILABLE = True
    logger.debug("[Gemini] google.genai SDK loaded successfully")
except ImportError:
    logger.warning(
        "[Gemini] google-genai not installed. Run: pip install google-genai"
    )


def _escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}") if text else text


class GeminiUnavailableError(Exception):
    """Raised when Gemini SDK is not installed or API key is missing."""


class GeminiProvider(BaseProvider):
    """
    Google Gemini 2.0 Flash provider using the google.genai SDK.

    Raises GeminiUnavailableError on init if SDK is missing or GEMINI_API_KEY is not set.
    Propagates google.api_core.exceptions.ResourceExhausted on rate limit so LLMRouter
    can catch it and fall back to the next tier.
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self, vector_store_service: VectorStoreService):
        if not _GEMINI_AVAILABLE:
            raise GeminiUnavailableError(
                "google-genai package not installed. Run: pip install google-genai"
            )
        if not GEMINI_API_KEYS:
            raise GeminiUnavailableError("GEMINI_API_KEY not set in environment.")

        self._clients = [_genai_client_cls(api_key=k) for k in GEMINI_API_KEYS]
        self.vector_store_service = vector_store_service
        logger.info("[Gemini] Provider initialized (model: %s)", self.MODEL)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        extra_parts: Optional[List[str]] = None,
        mode_addendum: str = "",
    ) -> str:
        """
        Builds the full system instruction: base + time + vector context + extras.
        Mirrors GroqProvider logic so responses are behaviorally consistent.
        """
        context = ""
        try:
            if self.vector_store_service:
                retriever = self.vector_store_service.get_retriever(k=5)
                docs = retriever.invoke(question)
                if docs:
                    context = "\n".join(d.page_content for d in docs)
        except Exception:
            pass

        time_info = get_time_information()
        system = JARVIS_SYSTEM_PROMPT + f"\n\nCurrent time and date: {time_info}"

        if context:
            system += f"\n\nRelevant context from learning data:\n{_escape_braces(context)}"
        if extra_parts:
            system += "\n\n" + "\n\n".join(extra_parts)
        if mode_addendum:
            system += f"\n\n{mode_addendum}"

        return system

    def _build_contents(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> list:
        """
        Converts [(human, ai), ...] history + current question into
        the google.genai Content list format.
        """
        contents = []
        for human_msg, ai_msg in (chat_history or []):
            contents.append(
                _genai_types.Content(
                    role="user",
                    parts=[_genai_types.Part(text=str(human_msg))],
                )
            )
            contents.append(
                _genai_types.Content(
                    role="model",
                    parts=[_genai_types.Part(text=str(ai_msg))],
                )
            )
        contents.append(
            _genai_types.Content(
                role="user",
                parts=[_genai_types.Part(text=question)],
            )
        )
        return contents

    def _generate_config(self) -> "_genai_types.GenerateContentConfig":
        return _genai_types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=1024,
        )

    def _gemini_grounded_search(self, query: str, client_index: int = 0) -> str:
        """
        Runs a Gemini-grounded Google Search request and returns the text result.

        This uses Gemini's built-in google_search tool — no Tavily API key needed,
        no extra cost. Results carry live citations sourced from Google's index.

        Returns an empty string on any failure so callers can gracefully fall back
        to the Tavily payload already injected by LLMRouter.
        """
        try:
            client = self._clients[client_index % len(self._clients)]
            response = client.models.generate_content(
                model=self.MODEL,
                contents=query,
                config=_genai_types.GenerateContentConfig(
                    tools=[_genai_types.Tool(google_search=_genai_types.GoogleSearch())],
                    temperature=0.1,        # factual — keep low
                    max_output_tokens=1024,
                ),
            )
            text = ""
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
            result = text.strip()
            if result:
                logger.info("[Gemini] Grounded search returned %d chars for: %.60s", len(result), query)
            else:
                logger.debug("[Gemini] Grounded search returned empty for: %.60s", query)
            return result
        except Exception as e:
            logger.warning("[Gemini] Grounded search failed (%s): %s", type(e).__name__, str(e)[:120])
            return ""

    # ── Public interface ───────────────────────────────────────────────────────

    def get_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,   # accepted for interface compat, unused
        use_search: bool = False,
    ) -> str:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM

        # ── Gemini grounded search (live web data, free) ────────────────────
        # When use_search is True we ask Gemini's own Google Search tool for
        # live data BEFORE building the conversational prompt.  The raw result
        # is prepended as a [LIVE WEB DATA] block so the model can cite it.
        extra_parts: List[str] = []
        if use_search:
            grounded = self._gemini_grounded_search(question, key_start_index)
            if grounded:
                extra_parts.append(
                    f"[LIVE WEB DATA — use this to answer the user's question, "
                    f"do not invent facts beyond what is shown below]:\n"
                    f"{_escape_braces(grounded)}"
                )

        system = self._build_system_prompt(
            question, chat_history,
            extra_parts=extra_parts if extra_parts else None,
            mode_addendum=mode,
        )
        contents = self._build_contents(question, chat_history)

        t0 = time.perf_counter()
        last_exc = None
        n = len(self._clients)
        for j in range(n):
            i = (key_start_index + j) % n
            try:
                response = self._clients[i].models.generate_content(
                    model=self.MODEL,
                    contents=contents,
                    config=_genai_types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.5,
                        max_output_tokens=4096,
                    ),
                )
                logger.info("[Gemini] get_response: %.3fs", time.perf_counter() - t0)
                return response.text or ""
            except Exception as e:
                logger.warning("[Gemini] Request failed with key %d (error: %s). Rotating to next key...", i + 1, str(e)[:100])
                last_exc = e
                if j < n - 1: continue
                break

        raise last_exc

    def stream_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
        **kwargs
    ) -> Iterator[Any]:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM
        extra = []
        if "tools_str" in kwargs and kwargs["tools_str"]:
            extra.append(kwargs["tools_str"])

        # ── Gemini grounded search on streaming path ────────────────────────
        if use_search:
            grounded = self._gemini_grounded_search(question, key_start_index)
            if grounded:
                extra.append(
                    f"[LIVE WEB DATA — use this to answer the user's question, "
                    f"do not invent facts beyond what is shown below]:\n"
                    f"{_escape_braces(grounded)}"
                )

        system = self._build_system_prompt(
            question, chat_history,
            extra_parts=extra if extra else None,
            mode_addendum=mode,
        )
        contents = self._build_contents(question, chat_history)

        last_exc = None
        n = len(self._clients)
        for j in range(n):
            i = (key_start_index + j) % n
            try:
                for chunk in self._clients[i].models.generate_content_stream(
                    model=self.MODEL,
                    contents=contents,
                    config=_genai_types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.5,
                        max_output_tokens=4096,
                    ),
                ):
                    try:
                        text = chunk.text
                        if text:
                            yield text
                    except Exception:
                        pass   # safety/metadata chunks with no text - skip
                return
            except Exception as e:
                logger.warning("[Gemini] Stream failed with key %d (error: %s). Rotating to next key...", i + 1, str(e)[:100])
                last_exc = e
                if j < n - 1: continue
                break
        raise last_exc

    def stream_response_with_prefetched(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        formatted_results: Optional[str] = None,
        payload: Optional[dict] = None,
        key_start_index: int = 0,
        **kwargs
    ) -> Iterator[Any]:
        extra = [_escape_braces(formatted_results)] if formatted_results else []
        if "tools_str" in kwargs and kwargs["tools_str"]:
            extra.append(kwargs["tools_str"])
        system = self._build_system_prompt(
            question, chat_history,
            extra_parts=extra if extra else None,
            mode_addendum=REALTIME_CHAT_ADDENDUM,
        )
        contents = self._build_contents(question, chat_history)

        last_exc = None
        n = len(self._clients)
        for j in range(n):
            i = (key_start_index + j) % n
            try:
                for chunk in self._clients[i].models.generate_content_stream(
                    model=self.MODEL,
                    contents=contents,
                    config=_genai_types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.5,
                        max_output_tokens=4096,
                    ),
                ):
                    try:
                        text = chunk.text
                        if text:
                            yield text
                    except Exception:
                        pass
                return
            except Exception as e:
                logger.warning("[Gemini] Prefetched stream failed with key %d (error: %s). Rotating to next key...", i + 1, str(e)[:100])
                last_exc = e
                if j < n - 1: continue
                break
        raise last_exc

    def prefetch_web_search(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> Tuple[str, Optional[dict]]:
        """
        Pre-fetch live web data via Gemini grounded search.

        Called by LLMRouter before routing so search results are available
        for all tiers (Gemini, GPT, Claude, Groq).  Previously this always
        returned ('', None), leaving T1 without any live data.

        Returns:
            (formatted_text, None) — None payload because Gemini grounded
            results arrive as plain text, not a structured payload dict.
            Callers that expect a Tavily-style dict (frontend search cards)
            will simply show no cards, which is acceptable.
        """
        if not question:
            return ("", None)
        try:
            result = self._gemini_grounded_search(question)
            return (result, None)
        except Exception as e:
            logger.warning("[Gemini] prefetch_web_search failed: %s", e)
            return ("", None)
