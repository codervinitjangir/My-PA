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
    GEMINI_API_KEY,
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
        if not GEMINI_API_KEY:
            raise GeminiUnavailableError("GEMINI_API_KEY not set in environment.")

        self._client = _genai_client_cls(api_key=GEMINI_API_KEY)
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

    # ── Public interface ───────────────────────────────────────────────────────

    def get_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,   # accepted for interface compat, unused
        use_search: bool = False,
    ) -> str:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM
        system = self._build_system_prompt(question, chat_history, mode_addendum=mode)
        contents = self._build_contents(question, chat_history)

        t0 = time.perf_counter()
        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=contents,
            config=_genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.5,
                max_output_tokens=1024,
            ),
        )
        logger.info("[Gemini] get_response: %.3fs", time.perf_counter() - t0)
        return response.text or ""

    def stream_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
    ) -> Iterator[Any]:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM
        system = self._build_system_prompt(question, chat_history, mode_addendum=mode)
        contents = self._build_contents(question, chat_history)

        for chunk in self._client.models.generate_content_stream(
            model=self.MODEL,
            contents=contents,
            config=_genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.5,
                max_output_tokens=1024,
            ),
        ):
            try:
                text = chunk.text
                if text:
                    yield text
            except Exception:
                pass   # safety/metadata chunks with no text — skip

    def stream_response_with_prefetched(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        formatted_results: Optional[str] = None,
        payload: Optional[dict] = None,
        key_start_index: int = 0,
    ) -> Iterator[Any]:
        extra = [_escape_braces(formatted_results)] if formatted_results else None
        system = self._build_system_prompt(
            question, chat_history,
            extra_parts=extra,
            mode_addendum=REALTIME_CHAT_ADDENDUM,
        )
        contents = self._build_contents(question, chat_history)

        for chunk in self._client.models.generate_content_stream(
            model=self.MODEL,
            contents=contents,
            config=_genai_types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.5,
                max_output_tokens=1024,
            ),
        ):
            try:
                text = chunk.text
                if text:
                    yield text
            except Exception:
                pass

    def prefetch_web_search(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> Tuple[str, Optional[dict]]:
        # Gemini does not own search — LLMRouter delegates this to Groq/Tavily.
        return ("", None)
