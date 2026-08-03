"""
app/services/news_search.py — Parallel News Search (First-Result-Wins)

Rewritten from Mark-L's web_search.py pattern, adapted to our codebase style.

How it works:
  - For news queries: fires Gemini grounded search AND DuckDuckGo news in two
    daemon threads simultaneously. Whichever delivers a valid result first wins;
    the other is silently discarded.
  - For general queries: Gemini grounded first, DDG text fallback (serial).
  - Modes: "news" | "search" | "research" | "price" | "compare"

Why parallel for news specifically:
  A Gemini 503 (quota) no longer adds latency. DDG is already running in
  parallel, so if Gemini fails the user sees DDG results in the same time as if
  only DDG had been called. Zero extra latency on the happy path.

Integration: Used by the LLM router's web prefetch and by the Telegram /news
command (added in telegram_bot.py).
"""

import hashlib
import logging
import re
import threading
from typing import Optional

logger = logging.getLogger("J.A.R.V.I.S.NewsSearch")

# ── DDG availability ──────────────────────────────────────────────────────────
_DDG_AVAILABLE = False
try:
    from duckduckgo_search import DDGS as _DDGS
    _DDG_AVAILABLE = True
except ImportError:
    try:
        from ddgs import DDGS as _DDGS  # alternate import name used in some versions
        _DDG_AVAILABLE = True
    except ImportError:
        logger.warning(
            "[NewsSearch] duckduckgo_search not installed. DDG fallback disabled. "
            "Run: pip install duckduckgo-search"
        )


# ── Internal DDG helpers ──────────────────────────────────────────────────────

def _ddg_news(query: str, max_results: int = 8) -> list:
    """Fetches DDG news results. Returns list of {title, snippet, url, source}."""
    if not _DDG_AVAILABLE:
        return []
    try:
        results = []
        with _DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", r.get("excerpt", "")),
                    "url":     r.get("url", r.get("link", "")),
                    "source":  r.get("source", r.get("publisher", "")),
                })
        return results
    except Exception as e:
        logger.debug("[NewsSearch] DDG news failed (%s): %s", type(e).__name__, e)
        # Fallback to text search
        try:
            results = []
            with _DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title":   r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url":     r.get("href", ""),
                        "source":  "",
                    })
            return results
        except Exception:
            return []


def _ddg_text(query: str, max_results: int = 6) -> list:
    """Fetches DDG text search results."""
    if not _DDG_AVAILABLE:
        return []
    try:
        results = []
        with _DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url":     r.get("href", ""),
                    "source":  "",
                })
        return results
    except Exception as e:
        logger.debug("[NewsSearch] DDG text failed (%s): %s", type(e).__name__, e)
        return []


def _format_news(query: str, results: list) -> str:
    if not results:
        return f"No news found for: {query}"
    lines = [f"Latest news — {query}\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "").strip()
        if not title:
            continue
        src = f"  [{r['source']}]" if r.get("source") else ""
        lines.append(f"{i}. {title}{src}")
        snippet = r.get("snippet", "")[:140]
        if snippet:
            lines.append(f"   {snippet}")
        url = r.get("url", "")
        if url:
            lines.append(f"   {url}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_search(query: str, results: list) -> str:
    if not results:
        return f"No results found for: {query}"
    lines = [f"Search results — {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):
            lines.append(f"{i}. {r['title']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        if r.get("url"):
            lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Gemini grounded search helper ─────────────────────────────────────────────

def _gemini_news_search(query: str) -> str:
    """
    Runs a Gemini grounded search using our existing GeminiProvider.
    Returns empty string on any failure — caller falls back to DDG.
    """
    try:
        import os
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            # Try multi-key env pattern
            from config import GEMINI_API_KEYS
            api_key = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
        if not api_key:
            return ""

        from google import genai
        from google.genai import types as _gtypes
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=query,
            config=_gtypes.GenerateContentConfig(
                tools=[_gtypes.Tool(google_search=_gtypes.GoogleSearch())],
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
        text = ""
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
        result = text.strip()
        if result and len(result) > 60:
            logger.debug("[NewsSearch] Gemini returned %d chars", len(result))
            return result
        return ""
    except Exception as e:
        logger.debug("[NewsSearch] Gemini grounded failed (%s): %s", type(e).__name__, str(e)[:100])
        return ""


# ── Public search functions ───────────────────────────────────────────────────

def search_news_parallel(query: str, timeout: float = 10.0) -> str:
    """
    Parallel news search — Gemini grounded + DDG news race.

    Fires both in daemon threads. Whichever delivers a valid result (len > 60)
    first is returned immediately; the other is silently discarded.
    If both fail within `timeout` seconds, returns a friendly fallback.

    This is the Mark-L pattern rewritten for our async/FastAPI codebase.
    Use this for time-sensitive news queries where latency matters.
    """
    result_box: list = [None]
    failures: list = [0]
    lock = threading.Lock()
    done = threading.Event()

    gemini_query = f"latest news today: {query}" if query else "top world news today"
    ddg_query = query if query else "world news today"

    def _store(text: str, source: str) -> None:
        if text and len(text) > 60:
            with lock:
                if result_box[0] is None:
                    result_box[0] = text
                    logger.info("[NewsSearch] Parallel winner: %s (%d chars)", source, len(text))
            done.set()
        else:
            with lock:
                failures[0] += 1
                if failures[0] >= 2:
                    done.set()  # both failed — unblock caller

    def _try_gemini():
        try:
            r = _gemini_news_search(gemini_query)
            _store(r, "gemini")
        except Exception as e:
            logger.debug("[NewsSearch] Gemini thread error: %s", e)
            _store("", "gemini")

    def _try_ddg():
        try:
            results = _ddg_news(ddg_query, max_results=8)
            _store(_format_news(ddg_query, results), "ddg")
        except Exception as e:
            logger.debug("[NewsSearch] DDG thread error: %s", e)
            _store("", "ddg")

    threading.Thread(target=_try_gemini, daemon=True, name="news-gemini").start()
    threading.Thread(target=_try_ddg,    daemon=True, name="news-ddg").start()

    done.wait(timeout=timeout)
    return result_box[0] or f"No news found for: {query}"


def search_general(query: str) -> str:
    """
    General-purpose search — Gemini grounded first, DDG text fallback (serial).
    For non-news, non-time-critical questions.
    """
    try:
        result = _gemini_news_search(query)
        if result:
            return result
    except Exception as e:
        logger.debug("[NewsSearch] Gemini general failed: %s", e)

    # DDG fallback
    results = _ddg_text(query, max_results=6)
    return _format_search(query, results) if results else f"No results found for: {query}"


def search_research(query: str) -> str:
    """Deep-dive research query — comprehensive Gemini grounded, wider DDG fallback."""
    research_q = (
        f"Comprehensive, detailed explanation of: {query}. "
        "Include background context, key facts, current state, and important nuances."
    )
    result = _gemini_news_search(research_q)
    if result:
        return result
    results = _ddg_text(query, max_results=10)
    return _format_search(query, results) if results else f"No results for: {query}"


def search_price(query: str) -> str:
    """Product price lookup."""
    price_q = f"current price of {query} — how much does it cost today"
    result = _gemini_news_search(price_q)
    if result:
        return result
    results = _ddg_text(f"{query} price buy", max_results=6)
    return _format_search(query, results) if results else f"No price data for: {query}"


def search_compare(items: list, aspect: str = "general") -> str:
    """Side-by-side comparison of items."""
    if not items:
        return "No items to compare."
    q = f"Compare {', '.join(items)} in terms of {aspect}. Give specific facts and data."
    result = _gemini_news_search(q)
    if result:
        return result
    # DDG per-item fallback
    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        results = _ddg_text(f"{item} {aspect}", max_results=3)
        lines.append(f"\n▸ {item}")
        for r in results[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
    return "\n".join(lines)


# ── Headline helper for briefing ──────────────────────────────────────────────

def fetch_headlines(n: int = 5) -> list:
    """
    Returns a list of current news headline strings via Gemini grounded search.
    Used by scheduler.py generate_briefing() to inject live headlines.
    Falls back to DDG news on Gemini failure.
    """
    try:
        prompt = f"Current world news: {n} headlines. Numbered list, titles only."
        raw = _gemini_news_search(prompt)
        if raw:
            headlines = []
            for line in raw.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                if not re.match(r'^[\d]+[.\)\-]', line):
                    continue
                clean = re.sub(r'^[\d]+[.\)\-]\s*', '', line)
                clean = re.sub(r'^\*+\s*', '', clean).strip()
                if clean and len(clean) > 10:
                    headlines.append(clean)
            if headlines:
                return headlines[:n]
    except Exception as e:
        logger.debug("[NewsSearch] fetch_headlines Gemini failed: %s", e)

    # DDG fallback
    results = _ddg_news("top world news today", max_results=n)
    return [r["title"] for r in results if r.get("title")][:n]


# ── Duplicate headline guard (for background monitor) ─────────────────────────

def headline_hash(title: str) -> str:
    """MD5 of headline title — used to detect duplicate alerts."""
    return hashlib.md5(title.encode("utf-8", errors="ignore")).hexdigest()[:12]
