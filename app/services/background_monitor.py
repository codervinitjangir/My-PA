"""
app/services/background_monitor.py — Background Topic Monitor

Allows the user to watch news topics ("Watch AI news for me").
Checks DDG news once per day per topic; only alerts when the headline hash
changes (i.e. genuinely new top story — no duplicate notifications).

Storage: uses our existing SQLite database (jarvis_memory.db) with a new
`topic_monitors` table. No separate JSON file — consistent with our architecture.

Inspired by Mark-L's background_monitor.py — rewritten for SQLite + our
MemoryService patterns. The blocked-topic list (crypto/finance) is preserved
as it's a strong UX design decision.

Public API:
  add_monitor(db_path, topic) → str message
  remove_monitor(db_path, topic) → str message
  list_monitors(db_path) → list[str]
  check_all_monitors(db_path) → list[str]   ← returns [MONITOR_ALERT] strings
"""

import hashlib
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("J.A.R.V.I.S.BackgroundMonitor")

# ── Blocked categories (never monitor regardless of user request) ─────────────
_BLOCKED = {
    # Crypto / blockchain — all major spellings / languages
    "bitcoin", "ethereum", "dogecoin", "solana", "binance",
    "nft", "blockchain", "defi", "altcoin", "memecoin", "coin", "token",
    "crypto", "kripto", "cripto", "krypto", "cryptocurrency",
}


def _is_blocked(topic: str) -> bool:
    t = topic.lower()
    return any(word in t for word in _BLOCKED)


def _slug(topic: str) -> str:
    """Normalises topic to a slug key for deduplication."""
    return re.sub(r"[^a-z0-9]+", "_", topic.lower().strip())[:40].strip("_")


def _headline_hash(title: str) -> str:
    return hashlib.md5(title.encode("utf-8", errors="ignore")).hexdigest()[:12]


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_conn(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def _ensure_table(db_path: str) -> None:
    """Creates the topic_monitors table if it doesn't exist."""
    with _get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_monitors (
                slug        TEXT PRIMARY KEY,
                topic       TEXT NOT NULL,
                added_on    TEXT NOT NULL,
                last_check  TEXT DEFAULT '',
                last_hash   TEXT DEFAULT ''
            )
        """)
        conn.commit()


# ── Public API ────────────────────────────────────────────────────────────────

def add_monitor(db_path: str, topic: str) -> str:
    """
    Adds a topic to the watch list.
    Returns a confirmation or refusal message.
    """
    topic = topic.strip()
    if not topic:
        return "Please specify a topic to monitor."
    if _is_blocked(topic):
        return "I don't monitor crypto or financial speculation topics."

    _ensure_table(db_path)
    slug = _slug(topic)

    with _get_conn(db_path) as conn:
        existing = conn.execute(
            "SELECT topic FROM topic_monitors WHERE slug = ?", (slug,)
        ).fetchone()
        if existing:
            return f"Already monitoring: {existing[0]}"

        conn.execute(
            "INSERT INTO topic_monitors (slug, topic, added_on, last_check, last_hash) "
            "VALUES (?, ?, ?, '', '')",
            (slug, topic, datetime.now().strftime("%Y-%m-%d")),
        )
        conn.commit()

    logger.info("[MONITOR] Added topic: %s", topic)
    return f"Now monitoring: **{topic}**. I'll alert you when new headlines appear."


def remove_monitor(db_path: str, topic: str) -> str:
    """Removes a topic from the watch list (exact slug or partial name match)."""
    topic_lower = topic.strip().lower()
    _ensure_table(db_path)

    with _get_conn(db_path) as conn:
        slug = _slug(topic_lower)
        row = conn.execute(
            "SELECT topic FROM topic_monitors WHERE slug = ?", (slug,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM topic_monitors WHERE slug = ?", (slug,))
            conn.commit()
            logger.info("[MONITOR] Removed topic: %s", row[0])
            return f"Stopped monitoring: **{row[0]}**"

        # Partial-match fallback
        rows = conn.execute(
            "SELECT slug, topic FROM topic_monitors"
        ).fetchall()
        for row_slug, row_topic in rows:
            if topic_lower in row_topic.lower():
                conn.execute("DELETE FROM topic_monitors WHERE slug = ?", (row_slug,))
                conn.commit()
                logger.info("[MONITOR] Removed topic (partial): %s", row_topic)
                return f"Stopped monitoring: **{row_topic}**"

    return f"Not found in monitored topics: {topic}"


def list_monitors(db_path: str) -> List[str]:
    """Returns a list of currently monitored topic names."""
    try:
        _ensure_table(db_path)
        with _get_conn(db_path) as conn:
            rows = conn.execute("SELECT topic FROM topic_monitors ORDER BY added_on").fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        logger.error("[MONITOR] list_monitors error: %s", e)
        return []


def check_all_monitors(db_path: str) -> List[str]:
    """
    Runs pending topic checks (once per day per topic via DDG news).
    Returns a list of [MONITOR_ALERT] strings — empty if nothing new.

    Should be called from a scheduler job (e.g. every hour or every morning).
    Uses our parallel news_search.py for the DDG news fetch.
    """
    try:
        _ensure_table(db_path)
        from app.services.news_search import _ddg_news, _headline_hash as hh
        # Use our module-level _headline_hash for consistency
    except Exception as e:
        logger.error("[MONITOR] check_all_monitors import error: %s", e)
        return []

    try:
        with _get_conn(db_path) as conn:
            monitors = conn.execute(
                "SELECT slug, topic, last_check, last_hash FROM topic_monitors"
            ).fetchall()
    except Exception as e:
        logger.error("[MONITOR] check_all_monitors DB read error: %s", e)
        return []

    if not monitors:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    alerts: List[str] = []

    for slug, topic, last_check, last_hash in monitors:
        if last_check == today:
            continue  # already checked today

        try:
            results = _ddg_news(topic, max_results=5)
            if not results:
                _update_check(db_path, slug, today, last_hash)
                continue

            top = results[0]
            title = top.get("title", "").strip()
            if not title:
                continue

            h = _headline_hash(title)
            if h == last_hash:
                # Same top headline as last check — no alert
                _update_check(db_path, slug, today, last_hash)
                continue

            # New headline — record and alert
            _update_check(db_path, slug, today, h)

            snippet = top.get("snippet", "")[:150]
            source  = top.get("source", "")
            parts = [
                f"[MONITOR_ALERT] Topic: {topic}",
                f"Headline: {title}",
            ]
            if snippet:
                parts.append(snippet)
            if source:
                parts.append(f"Source: {source}")

            alerts.append("\n".join(parts))
            logger.info("[MONITOR] New headline for '%s': %s", topic, title[:60])

        except Exception as e:
            logger.warning("[MONITOR] Check failed for '%s': %s", topic, e)

    return alerts


def _update_check(db_path: str, slug: str, today: str, h: str) -> None:
    """Updates last_check and last_hash for a topic."""
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                "UPDATE topic_monitors SET last_check = ?, last_hash = ? WHERE slug = ?",
                (today, h, slug),
            )
            conn.commit()
    except Exception as e:
        logger.error("[MONITOR] _update_check error for %s: %s", slug, e)
