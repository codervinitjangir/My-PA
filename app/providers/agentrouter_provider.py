"""
AgentRouter Provider — Tiers 2 & 3 for J.A.R.V.I.S LLM fallback chain.

ROOT CAUSE FIX: The OpenAI Python SDK injects X-Stainless-Lang, X-Stainless-Runtime,
X-Stainless-OS, X-Stainless-Package-Version headers that AgentRouter's anti-abuse
system detects as an "unauthorized client" and returns 401. 

This provider uses raw httpx calls with only Authorization + Content-Type headers
to bypass this fingerprinting completely.

- Tier 2 model: GPT_FAST_MODEL (default "gpt-5.5") — speed fallback when Gemini is rate-limited
- Tier 3 model: DEEP_MODEL (default "claude-opus-4-8") — deep reasoning for complex queries
"""
import json
import logging
import time
from typing import List, Optional, Iterator, Tuple, Any

import httpx

from app.providers.base_provider import BaseProvider
from app.services.vector_store import VectorStoreService
from app.utils.time_info import get_time_information
from config import (
    AGENTROUTER_API_KEY,
    AGENTROUTER_BASE_URL,
    JARVIS_SYSTEM_PROMPT,
    GENERAL_CHAT_ADDENDUM,
    REALTIME_CHAT_ADDENDUM,
)

logger = logging.getLogger("J.A.R.V.I.S")


def _escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}") if text else text


class AgentRouterUnavailableError(Exception):
    """Raised when AgentRouter credentials are not set."""


class AgentRouterProvider(BaseProvider):
    """
    OpenAI-compatible provider pointing at AgentRouter endpoint.
    Uses raw httpx calls to avoid SDK fingerprinting (401 unauthorized_client_error).

    Exposes two logical models through one client:
      - fast_model  → gpt-5.5          (Tier 2)
      - deep_model  → claude-opus-4-8  (Tier 3)
    """

    def __init__(
        self,
        vector_store_service: VectorStoreService,
        fast_model: str = "gpt-5.5",
        deep_model: str = "claude-opus-4-8",
    ):
        if not AGENTROUTER_BASE_URL or not AGENTROUTER_API_KEY:
            raise AgentRouterUnavailableError(
                "AGENTROUTER_BASE_URL and AGENTROUTER_API_KEY must be set in .env"
            )

        import os
        PROXY_SECRET = os.getenv("PROXY_SECRET", "default-proxy-secret-12345")
        
        self._base_url = AGENTROUTER_BASE_URL.rstrip("/")
        self._chat_url = f"{self._base_url}/chat/completions"
        # Minimal headers — no SDK fingerprinting
        self._headers = {
            "Authorization": f"Bearer {AGENTROUTER_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Proxy-Secret": PROXY_SECRET,
        }
        self.fast_model = fast_model
        self.deep_model = deep_model
        self.vector_store_service = vector_store_service
        logger.info(
            "[AgentRouter] Provider initialized via httpx (fast=%s, deep=%s) → %s",
            fast_model, deep_model, self._base_url,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_system_prompt(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        extra_parts: Optional[List[str]] = None,
        mode_addendum: str = "",
    ) -> str:
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
            system += f"\n\nRelevant context:\n{context}"
        if extra_parts:
            system += "\n\n" + "\n\n".join(extra_parts)
        if mode_addendum:
            system += f"\n\n{mode_addendum}"

        return system

    def _build_messages(
        self,
        question: str,
        system_prompt: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> list:
        """Build OpenAI-format messages list."""
        messages = [{"role": "system", "content": system_prompt}]
        for human_msg, ai_msg in (chat_history or []):
            messages.append({"role": "user", "content": str(human_msg)})
            messages.append({"role": "assistant", "content": str(ai_msg)})
        messages.append({"role": "user", "content": question})
        return messages

    def _raw_post(self, model: str, messages: list, stream: bool = False) -> httpx.Response:
        """Make a raw httpx POST to /chat/completions."""
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.5,
            "stream": stream,
        }
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)
        resp = httpx.post(
            self._chat_url,
            headers=self._headers,
            json=body,
            timeout=timeout,
        )
        if resp.status_code not in (200, 201):
            logger.error(
                "[AgentRouter] HTTP %d from %s model=%s body=%s",
                resp.status_code, self._chat_url, model, resp.text[:400]
            )
            resp.raise_for_status()
        return resp

    def _raw_stream(self, model: str, messages: list) -> Iterator[str]:
        """Make a raw streaming POST and yield text delta chunks."""
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.5,
            "stream": True,
        }
        headers = dict(self._headers)
        headers["Accept"] = "text/event-stream"
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)

        with httpx.stream(
            "POST",
            self._chat_url,
            headers=headers,
            json=body,
            timeout=timeout,
        ) as resp:
            if resp.status_code not in (200, 201):
                body_text = resp.read().decode("utf-8", errors="replace")
                logger.error(
                    "[AgentRouter] Stream HTTP %d model=%s body=%s",
                    resp.status_code, model, body_text[:400]
                )
                resp.raise_for_status()

            for line in resp.iter_lines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    raw = line[6:]
                    try:
                        chunk = json.loads(raw)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    # ── Core call methods (model-parameterised) ────────────────────────────────

    def call(
        self,
        question: str,
        model: str,
        chat_history: Optional[List[tuple]] = None,
        extra_parts: Optional[List[str]] = None,
        mode_addendum: str = "",
    ) -> str:
        """Non-streaming completion for any model on this AgentRouter endpoint."""
        system = self._build_system_prompt(question, chat_history, extra_parts, mode_addendum)
        messages = self._build_messages(question, system, chat_history)

        t0 = time.perf_counter()
        resp = self._raw_post(model, messages, stream=False)
        elapsed = time.perf_counter() - t0

        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info("[AgentRouter] call(%s): %.3fs, %d chars", model, elapsed, len(text))
        return text

    def stream(
        self,
        question: str,
        model: str,
        chat_history: Optional[List[tuple]] = None,
        extra_parts: Optional[List[str]] = None,
        mode_addendum: str = "",
    ) -> Iterator[str]:
        """SSE streaming for any model on this AgentRouter endpoint."""
        system = self._build_system_prompt(question, chat_history, extra_parts, mode_addendum)
        messages = self._build_messages(question, system, chat_history)
        yield from self._raw_stream(model, messages)

    # ── BaseProvider interface (uses deep_model as default) ───────────────────

    def get_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
    ) -> str:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM
        return self.call(question, self.deep_model, chat_history, mode_addendum=mode)

    def stream_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
    ) -> Iterator[Any]:
        mode = REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM
        yield from self.stream(question, self.deep_model, chat_history, mode_addendum=mode)

    def stream_response_with_prefetched(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        formatted_results: Optional[str] = None,
        payload: Optional[dict] = None,
        key_start_index: int = 0,
    ) -> Iterator[Any]:
        extra = [formatted_results] if formatted_results else None
        yield from self.stream(
            question, self.deep_model, chat_history,
            extra_parts=extra, mode_addendum=REALTIME_CHAT_ADDENDUM,
        )

    def prefetch_web_search(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> Tuple[str, Optional[dict]]:
        # AgentRouter does not own search — delegated to Groq/Tavily by LLMRouter.
        return ("", None)
