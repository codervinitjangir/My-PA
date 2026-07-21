"""
LLMRouter — 4-Tier Intelligent Fallback Chain for J.A.R.V.I.S.

Routing strategy
────────────────
Tier 1  Gemini 2.0 Flash        — Primary. Fast, capable, free-tier friendly.
Tier 2  GPT-5.5 (AgentRouter)   — Auto-fallback when Gemini is rate-limited or erroring.
Tier 3  Claude Opus 4-8         — Complex queries OR when GPT-5.5 fails.
Tier 4  Groq Llama 70B          — Emergency backstop. Always available.

Complexity detection
────────────────────
Routes directly to Tier 3 (Claude Opus) if:
  - message length > 200 chars, OR
  - message contains any complexity keyword

Streaming fallback contract
───────────────────────────
Once the first chunk has been yielded from a provider, that provider owns the stream.
Fallback only happens if the failure occurs BEFORE any content is yielded (connection
error, auth failure, rate limit on first call). This prevents garbled partial responses.

Duck-typing
───────────
This class exposes exactly the same interface as GroqProvider so it can be passed as
`groq_service` to ChatService, TaskExecutor, etc. with zero changes in those files.
"""
import logging
import time
from typing import List, Optional, Iterator, Tuple, Any

from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider, GeminiUnavailableError
from app.providers.agentrouter_provider import AgentRouterProvider, AgentRouterUnavailableError
from config import GPT_FAST_MODEL, DEEP_MODEL

logger = logging.getLogger("J.A.R.V.I.S")

# ── Complexity detection ────────────────────────────────────────────────────────
_COMPLEXITY_KEYWORDS = frozenset([
    "review", "analyze", "analyse", "design", "architecture",
    "compare", "evaluate", "explain why", "debug", "optimize", "optimise",
    "refactor", "deep dive", "trade-off", "tradeoff", "trade off",
])
_COMPLEXITY_LENGTH_THRESHOLD = 200


def is_complex(message: str) -> bool:
    """
    Returns True if the query warrants Tier 3 (Claude Opus) directly.
    Fast O(n) check: length + keyword scan.
    """
    if len(message) > _COMPLEXITY_LENGTH_THRESHOLD:
        return True
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in _COMPLEXITY_KEYWORDS)


class LLMRouter:
    """
    4-tier LLM fallback chain. Drop-in replacement for GroqProvider.

    Initialisation is tolerant: if Gemini or AgentRouter are not available (missing key /
    missing package), they are set to None and the router gracefully skips them.
    """

    def __init__(
        self,
        groq_provider: GroqProvider,
        gemini_provider: Optional[GeminiProvider],
        agentrouter_provider: Optional[AgentRouterProvider],
    ):
        self.groq_provider = groq_provider
        self.gemini = gemini_provider
        self.agent_router = agentrouter_provider

        # Expose vector_store_service attribute so ChatService.update_vector_store_live works
        self.vector_store_service = groq_provider.vector_store_service

        available = ["Groq (T4)"]
        if self.agent_router:
            available = [f"Claude Opus/{DEEP_MODEL} (T3)", f"GPT-5.5/{GPT_FAST_MODEL} (T2)"] + available
        if self.gemini:
            available = ["Gemini Flash (T1)"] + available
        logger.info("[LLMRouter] Active tiers: %s", " → ".join(available))

    # ── Complexity routing ──────────────────────────────────────────────────────

    def _log_routing(self, tier: int, model: str, reason: str):
        labels = {1: "Gemini Flash", 2: f"GPT-5.5 ({GPT_FAST_MODEL})",
                  3: f"Claude Opus ({DEEP_MODEL})", 4: "Groq Llama 70B"}
        logger.info("[LLM] Using %s — %s", labels.get(tier, model), reason)

    # ── Non-streaming: get_response ─────────────────────────────────────────────

    def get_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
    ) -> str:
        """
        Non-streaming call with full 4-tier fallback.
        Complexity → Tier 3 directly; otherwise Tier 1 → 2 → 3 → 4.
        """
        if is_complex(question) and self.agent_router:
            self._log_routing(3, DEEP_MODEL, "complex query detected")
            try:
                return self.agent_router.call(
                    question, DEEP_MODEL, chat_history,
                    mode_addendum=self._mode(use_search),
                )
            except Exception as e:
                logger.warning("[LLM] Claude Opus failed (%s) → Groq (T4)", type(e).__name__)
            return self.groq_provider.get_response(question, chat_history, key_start_index, use_search)

        # Tier 1 — Gemini
        if self.gemini:
            try:
                self._log_routing(1, "gemini-2.0-flash", "primary")
                return self.gemini.get_response(question, chat_history, key_start_index, use_search)
            except Exception as e:
                logger.warning("[LLM] Gemini failed (%s) → GPT-5.5 (T2)", type(e).__name__)

        # Tier 2 — GPT-5.5
        if self.agent_router:
            try:
                self._log_routing(2, GPT_FAST_MODEL, "Gemini fallback")
                return self.agent_router.call(
                    question, GPT_FAST_MODEL, chat_history,
                    mode_addendum=self._mode(use_search),
                )
            except Exception as e:
                logger.warning("[LLM] GPT-5.5 failed (%s) → Claude Opus (T3)", type(e).__name__)

            # Tier 3 — Claude Opus
            try:
                self._log_routing(3, DEEP_MODEL, "GPT-5.5 fallback")
                return self.agent_router.call(
                    question, DEEP_MODEL, chat_history,
                    mode_addendum=self._mode(use_search),
                )
            except Exception as e:
                logger.warning("[LLM] Claude Opus failed (%s) → Groq (T4)", type(e).__name__)

        # Tier 4 — Groq (always available)
        self._log_routing(4, "groq-llama-70b", "emergency fallback")
        return self.groq_provider.get_response(question, chat_history, key_start_index, use_search)

    # ── Streaming helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _mode(use_search: bool) -> str:
        from config import REALTIME_CHAT_ADDENDUM, GENERAL_CHAT_ADDENDUM
        return REALTIME_CHAT_ADDENDUM if use_search else GENERAL_CHAT_ADDENDUM

    def _try_stream(self, gen_fn, provider_name: str = "unknown", prompt_size: int = 0) -> Tuple[Optional[Iterator], bool]:
        """
        Attempts to prime a generator by fetching the first chunk.
        Returns (iterator_with_first_chunk_pre-pended, success_flag).
        On failure returns (None, False).
        """
        import itertools
        try:
            gen = gen_fn()
            first = next(gen)            # probe — raises immediately on connection failure
            logger.info("[LLM] Tier used: %s", provider_name)
            if prompt_size > 0:
                logger.info("[LLM] System prompt size: %d characters / ~%d estimated tokens", prompt_size, prompt_size // 4)
            return itertools.chain([first], gen), True
        except StopIteration:
            return iter([]), True        # empty but valid stream
        except Exception as e:
            logger.warning("[LLM] Stream probe failed (%s): %s", type(e).__name__, str(e)[:120])
            return None, False

    # ── Streaming: stream_response ──────────────────────────────────────────────

    def stream_response(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        key_start_index: int = 0,
        use_search: bool = False,
        **kwargs
    ) -> Iterator[Any]:
        """
        Streaming call with 4-tier fallback.
        Fallback only triggers if the failure occurs before the first chunk.
        Once streaming has started, that provider owns the stream.
        """
        # ── If search results needed and we have search infrastructure ──────────
        # For Gemini/AgentRouter, pre-fetch search here so they can inject it.
        formatted_results = ""
        search_payload = None
        if use_search:
            try:
                formatted_results, search_payload = self.groq_provider.prefetch_web_search(
                    question, chat_history
                )
            except Exception as e:
                logger.warning("[LLM] Search pre-fetch failed: %s", e)
                
        # Estimate prompt size
        from config import JARVIS_SYSTEM_PROMPT
        base = len(JARVIS_SYSTEM_PROMPT)
        hist = sum(len(h) + len(a) for h, a in chat_history) if chat_history else 0
        search = len(formatted_results) if formatted_results else 0
        tools = len(kwargs.get("tools_str", ""))
        prompt_size = base + hist + search + tools + len(question) + 300

        def _gemini_stream():
            if formatted_results:
                yield from self.gemini.stream_response_with_prefetched(
                    question, chat_history, formatted_results, search_payload, **kwargs
                )
            else:
                yield from self.gemini.stream_response(question, chat_history, key_start_index, use_search, **kwargs)

        def _gpt_stream():
            mode = self._mode(use_search)
            extra = [formatted_results] if formatted_results else []
            tools_str = kwargs.get("tools_str", "")
            if tools_str: extra.append(tools_str)
            yield from self.agent_router.stream(question, GPT_FAST_MODEL, chat_history,
                                                extra_parts=extra if extra else None, mode_addendum=mode)

        def _claude_stream():
            mode = self._mode(use_search)
            extra = [formatted_results] if formatted_results else []
            tools_str = kwargs.get("tools_str", "")
            if tools_str: extra.append(tools_str)
            yield from self.agent_router.stream(question, DEEP_MODEL, chat_history,
                                                extra_parts=extra if extra else None, mode_addendum=mode)

        def _groq_stream():
            if formatted_results:
                yield from self.groq_provider.stream_response_with_prefetched(
                    question, chat_history, formatted_results, search_payload, key_start_index, **kwargs
                )
            else:
                yield from self.groq_provider.stream_response(question, chat_history, key_start_index, use_search, **kwargs)

        # Route complex queries directly to Tier 3
        if is_complex(question) and self.agent_router:
            self._log_routing(3, DEEP_MODEL, "complex query — stream")
            stream, ok = self._try_stream(_claude_stream, "agentrouter (claude)", prompt_size)
            if ok:
                yield from stream
                return
            logger.warning("[LLM] Claude Opus stream failed → Groq (T4)")
            logger.info("[LLM] Tier used: groq")
            logger.info("[LLM] System prompt size: %d characters / ~%d estimated tokens", prompt_size, prompt_size // 4)
            yield from _groq_stream()
            return

        # Tier 1 — Gemini
        if self.gemini:
            self._log_routing(1, "gemini-2.0-flash", "primary stream")
            stream, ok = self._try_stream(_gemini_stream, "gemini", prompt_size)
            if ok:
                yield from stream
                return
            logger.warning("[LLM] Gemini stream failed → GPT-5.5 (T2)")

        # Tier 2 — GPT-5.5
        if self.agent_router:
            self._log_routing(2, GPT_FAST_MODEL, "Gemini fallback stream")
            stream, ok = self._try_stream(_gpt_stream, "agentrouter (gpt-5.5)", prompt_size)
            if ok:
                yield from stream
                return
            logger.warning("[LLM] GPT-5.5 stream failed → Claude Opus (T3)")

            # Tier 3 — Claude Opus
            self._log_routing(3, DEEP_MODEL, "GPT-5.5 fallback stream")
            stream, ok = self._try_stream(_claude_stream, "agentrouter (claude)", prompt_size)
            if ok:
                yield from stream
                return
            logger.warning("[LLM] Claude Opus stream failed → Groq (T4)")

        # Tier 4 — Groq
        self._log_routing(4, "groq-llama-70b", "emergency stream fallback")
        logger.info("[LLM] Tier used: groq")
        logger.info("[LLM] System prompt size: %d characters / ~%d estimated tokens", prompt_size, prompt_size // 4)
        yield from _groq_stream()

    # ── Streaming: stream_response_with_prefetched ──────────────────────────────

    def stream_response_with_prefetched(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
        formatted_results: Optional[str] = None,
        payload: Optional[dict] = None,
        key_start_index: int = 0,
        **kwargs
    ) -> Iterator[Any]:
        """
        Streaming with pre-fetched search results. Same 4-tier routing.
        Used by process_jarvis_message_stream for realtime/task routes.
        """
        def _gemini_stream():
            yield from self.gemini.stream_response_with_prefetched(
                question, chat_history, formatted_results, payload
            )

        def _gpt_stream():
            extra = [formatted_results] if formatted_results else None
            yield from self.agent_router.stream(
                question, GPT_FAST_MODEL, chat_history,
                extra_parts=extra, mode_addendum=self._mode(True),
            )

        def _claude_stream():
            extra = [formatted_results] if formatted_results else None
            yield from self.agent_router.stream(
                question, DEEP_MODEL, chat_history,
                extra_parts=extra, mode_addendum=self._mode(True),
            )

        def _groq_stream():
            yield from self.groq_provider.stream_response_with_prefetched(
                question, chat_history, formatted_results, payload, key_start_index
            )

        if is_complex(question) and self.agent_router:
            self._log_routing(3, DEEP_MODEL, "complex prefetched stream")
            stream, ok = self._try_stream(_claude_stream)
            if ok:
                yield from stream
                return
            yield from _groq_stream()
            return

        if self.gemini:
            self._log_routing(1, "gemini-2.0-flash", "prefetched stream")
            stream, ok = self._try_stream(_gemini_stream)
            if ok:
                yield from stream
                return

        if self.agent_router:
            self._log_routing(2, GPT_FAST_MODEL, "Gemini fallback prefetched")
            stream, ok = self._try_stream(_gpt_stream)
            if ok:
                yield from stream
                return

            self._log_routing(3, DEEP_MODEL, "GPT-5.5 fallback prefetched")
            stream, ok = self._try_stream(_claude_stream)
            if ok:
                yield from stream
                return

        self._log_routing(4, "groq-llama-70b", "emergency prefetched fallback")
        yield from _groq_stream()

    # ── Delegation: keep Groq utilities accessible ───────────────────────────────

    def prefetch_web_search(
        self,
        question: str,
        chat_history: Optional[List[tuple]] = None,
    ) -> Tuple[str, Optional[dict]]:
        """Tavily search is always handled by Groq's client. Unchanged."""
        return self.groq_provider.prefetch_web_search(question, chat_history)

    def set_model(self, new_model: str) -> None:
        """
        Forwards /set_model command to GroqProvider for backward compat.
        Also updates AgentRouter deep_model if the model looks like a claude/gpt name.
        """
        self.groq_provider.set_model(new_model)
        if self.agent_router:
            # Heuristic: if the new model contains "claude" set it as deep model
            if "claude" in new_model.lower():
                self.agent_router.deep_model = new_model
                logger.info("[LLMRouter] AgentRouter deep_model updated to: %s", new_model)
            elif "gpt" in new_model.lower():
                self.agent_router.fast_model = new_model
                logger.info("[LLMRouter] AgentRouter fast_model updated to: %s", new_model)
