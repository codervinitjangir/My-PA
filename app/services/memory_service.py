import sqlite3
import logging
import threading
import json
import os
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import json

from app.utils.redact import redact_text

logger = logging.getLogger("J.A.R.V.I.S.Memory")

class MemoryService:
    def __init__(self, db_path: str = "database/jarvis_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        backup_b64 = os.environ.get("MEMORY_BACKUP_B64")
        if backup_b64:
            if not self.db_path.exists() or self.db_path.stat().st_size == 0:
                try:
                    logger.info("[MEMORY] Restoring database from MEMORY_BACKUP_B64...")
                    with open(self.db_path, "wb") as f:
                        f.write(base64.b64decode(backup_b64))
                    logger.info("[MEMORY] Database restored successfully.")
                except Exception as e:
                    logger.error("[MEMORY] Failed to restore database from backup: %s", e)
                    
        self._init_db()
        self._auto_cleanup()
        
    def _get_conn(self):
        # sqlite3 needs check_same_thread=False if shared, but best practice is new connection per thread
        return sqlite3.connect(self.db_path)
        
    def _init_db(self):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        category TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Try to add date_reference column if it doesn't exist
                try:
                    cursor.execute("ALTER TABLE knowledge ADD COLUMN date_reference TEXT")
                except sqlite3.OperationalError:
                    pass
                try:
                    cursor.execute("ALTER TABLE knowledge ADD COLUMN followed_up BOOLEAN DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
                conn.commit()
                logger.info("[MEMORY] SQLite DB initialized at %s", self.db_path)
        except Exception as e:
            logger.error("[MEMORY] DB init failed: %s", e)

    def _auto_cleanup(self):
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # Delete older than 30 days
                thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("DELETE FROM summaries WHERE created_at < ?", (thirty_days_ago,))
                
                # Keep max 10 per session
                cursor.execute("SELECT DISTINCT session_id FROM summaries")
                sessions = cursor.fetchall()
                for (session_id,) in sessions:
                    cursor.execute("""
                        DELETE FROM summaries 
                        WHERE id NOT IN (
                            SELECT id FROM summaries 
                            WHERE session_id = ? 
                            ORDER BY created_at DESC 
                            LIMIT 10
                        ) AND session_id = ?
                    """, (session_id, session_id))
                
                conn.commit()
                logger.info("[MEMORY] Cleanup completed")
        except Exception as e:
            logger.error("[MEMORY] Cleanup failed: %s", e)

    def backup(self) -> str:
        if not self.db_path.exists():
            return ""
        try:
            with open(self.db_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error("[MEMORY] Failed to backup database: %s", e)
            return ""

    def maybe_summarise(self, session_id: str, messages: List[any], llm_router) -> Optional[str]:
        # Compact if messages exceed 15. Keep last 6 out of the summary.
        if not messages or len(messages) <= 15:
            return None
            
        logger.info("[MEMORY] Triggering background summary for session %s (msgs: %d)", session_id, len(messages))
        
        try:
            # Format history for prompt: all but the last 6 messages
            history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages[:-6]])
            
            prompt = (
                "You are JARVIS. Summarise the following recent conversation into EXACTLY "
                "one concise paragraph (max 150 words). Capture key context, facts, and state. "
                "Also capture any notable/memorable moments (e.g. funny exchanges, interesting tangents) separately from factual summaries. "
                "Do NOT include conversational filler.\n\n"
                f"Conversation:\n{history_text}"
            )
            
            # Using the router to get response (benefits from fallback chain)
            summary = llm_router.get_response(prompt)
            
            summary = redact_text(summary)
            
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO summaries (session_id, summary) VALUES (?, ?)", 
                    (session_id, summary.strip())
                )
                conn.commit()
                logger.info("[MEMORY] Saved session summary")
                
            return summary.strip()
                
        except Exception as e:
            logger.error("[MEMORY] Summarisation failed: %s", e)
            return None

    def store_knowledge(self, content: str, llm_router, force_update_id: int = None, force_category: str = None, date_reference: str = None) -> str:
        try:
            content = redact_text(content)
            
            if force_update_id is not None:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE knowledge SET content = ?, updated_at = CURRENT_TIMESTAMP, date_reference = COALESCE(?, date_reference) WHERE id = ?",
                        (content, date_reference, force_update_id)
                    )
                    conn.commit()
                cat = force_category or "fact"
                return f"Updated existing {cat} memory."
                
            prompt = (
                "Categorize the following information into exactly ONE of these categories: "
                "preference, project, person, decision, fact, procedural, resource.\n"
                "- procedural: how the user likes things done (e.g., 'always confirm before sending emails')\n"
                "- resource: references to files/documents handled (e.g., 'the Q3 report PDF sent last week')\n"
                "Return ONLY the category name in lowercase, nothing else.\n"
                f"Information: {content}"
            )
            category = llm_router.get_response(prompt).strip().lower()
            
            valid_cats = ["preference", "project", "person", "decision", "fact", "procedural", "resource"]
            if category not in valid_cats:
                category = "fact"
                
            # Check for overlap
            words_new = set(content.lower().split())
            best_match_id = None
            best_overlap = 0.0
            
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, content FROM knowledge WHERE category = ?", (category,))
                existing_rows = cursor.fetchall()
                
                for row_id, existing_content in existing_rows:
                    words_exist = set(existing_content.lower().split())
                    if not words_new or not words_exist:
                        continue
                    overlap = len(words_new.intersection(words_exist)) / max(len(words_new), len(words_exist))
                    if overlap > 0.5 and overlap > best_overlap:
                        best_overlap = overlap
                        best_match_id = row_id
                        
                if best_match_id:
                    # CONTRADICTION CHECK
                    try:
                        existing_contents = [c for r_id, c in existing_rows]
                        numbered_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(existing_contents)])
                        check_prompt = (
                            f"Does this new fact contradict any existing fact?\n"
                            f"New: {content}\n"
                            f"Existing:\n{numbered_list}\n"
                            "Reply STRICTLY in JSON format: {\"contradicts\": bool, \"conflicting_id\": int|null, \"explanation\": \"str\"}"
                        )
                        resp = llm_router.get_response(check_prompt).strip()
                        if resp.startswith('```json'): resp = resp[7:-3]
                        elif resp.startswith('```'): resp = resp[3:-3]
                        parsed = json.loads(resp)
                        if parsed.get("contradicts") and parsed.get("explanation"):
                            return f"__CONTRADICT__:{best_match_id}:{category}:{content}::{parsed.get('explanation')}"
                    except Exception as e:
                        logger.error("[MEMORY] Contradiction check failed, failing open: %s", e)
                        
                    cursor.execute(
                        "UPDATE knowledge SET content = ?, updated_at = CURRENT_TIMESTAMP, date_reference = COALESCE(?, date_reference) WHERE id = ?",
                        (content, date_reference, best_match_id)
                    )
                    conn.commit()
                    return f"Updated existing {category} memory."
                else:
                    cursor.execute(
                        "INSERT INTO knowledge (content, category, date_reference) VALUES (?, ?, ?)",
                        (content, category, date_reference)
                    )
                    conn.commit()
                    return f"Stored new {category} memory."
                    
        except Exception as e:
            logger.error("[MEMORY] Store knowledge failed: %s", e)
            return "Failed to store memory due to an error."

    def forget_knowledge(self, keyword: str) -> str:
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM knowledge WHERE content LIKE ?", 
                    (f"%{keyword}%",)
                )
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    return f"Deleted {deleted} memory items matching '{keyword}'."
                return f"No memories found matching '{keyword}'."
        except Exception as e:
            logger.error("[MEMORY] Forget knowledge failed: %s", e)
            return "Error deleting memory."

    def forget_all(self) -> str:
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM knowledge")
                conn.commit()
                return "All explicit memories have been erased."
        except Exception as e:
            logger.error("[MEMORY] Forget all failed: %s", e)
            return "Error erasing memory."

    def get_all_knowledge(self) -> str:
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT category, content FROM knowledge ORDER BY category")
                rows = cursor.fetchall()
                
                if not rows:
                    return "No memories stored."
                    
                output = "🧠 **J.A.R.V.I.S. Knowledge Bank**\n\n"
                current_cat = None
                for cat, content in rows:
                    if cat != current_cat:
                        output += f"\n*{cat.upper()}*\n"
                        current_cat = cat
                    output += f"- {content}\n"
                return output
        except Exception as e:
            return f"Error retrieving memories: {e}"

    def build_memory_context(self, session_id: str, query: str, recent_messages: List[str] = None) -> str:
        try:
            # Recall Gate
            if recent_messages:
                query_words = set(w for w in query.lower().split() if len(w) > 3)
                if query_words:
                    for msg in recent_messages:
                        msg_words = set(w for w in msg.lower().split() if len(w) > 3)
                        if msg_words:
                            overlap = len(query_words.intersection(msg_words)) / max(len(query_words), len(msg_words))
                            if overlap > 0.6:
                                logger.info("[MEMORY] Recall gate triggered (overlap %.2f) — skipping fetch", overlap)
                                return ""
                                
            tech_keywords = ["code", "api", "build", "deploy", "bug", "error", "script", "python", "git", "terminal", "server", "database", "function", "class"]
            is_tech = any(kw in query.lower() for kw in tech_keywords)
            
            # Prioritise by category relevance but always retrieve all categories
            # Tech queries: project/decision first; general: preference/fact first
            priority_cats = ["project", "decision", "person"] if is_tech else ["preference", "fact", "person"]
            secondary_cats = ["preference", "fact"] if is_tech else ["project", "decision"]
            ordered_cats = priority_cats + secondary_cats
            
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # Top 3 summaries for this session
                cursor.execute("""
                    SELECT summary FROM summaries 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC LIMIT 3
                """, (session_id,))
                summaries = [row[0] for row in cursor.fetchall()]
                
                # Fetch top 5 knowledge items: priority categories first, then recency
                placeholders_priority = ','.join('?' for _ in priority_cats)
                placeholders_secondary = ','.join('?' for _ in secondary_cats)
                query_sql = f"""
                    SELECT content, category FROM knowledge 
                    WHERE category IN ({placeholders_priority})
                    ORDER BY updated_at DESC LIMIT 4
                """
                cursor.execute(query_sql, priority_cats)
                priority_knowledge = cursor.fetchall()
                
                # Fill remaining slots from secondary categories
                remaining = max(0, 5 - len(priority_knowledge))
                if remaining > 0:
                    query_sql2 = f"""
                        SELECT content, category FROM knowledge 
                        WHERE category IN ({placeholders_secondary})
                        ORDER BY updated_at DESC LIMIT {remaining}
                    """
                    cursor.execute(query_sql2, secondary_cats)
                    secondary_knowledge = cursor.fetchall()
                else:
                    secondary_knowledge = []
                    
            knowledge = [row[0] for row in priority_knowledge + secondary_knowledge]
                
            if not summaries and not knowledge:
                return ""
                
            ctx = "\n[JARVIS MEMORY]\n"
            if summaries:
                ctx += "Recent Session Summaries:\n" + "\n".join(f"- {s}" for s in summaries) + "\n\n"
            if knowledge:
                ctx += "Relevant Knowledge Base:\n" + "\n".join(f"- {k}" for k in knowledge) + "\n"
            ctx += "[END MEMORY]\n"
            
            return ctx
            
        except Exception as e:
            logger.error("[MEMORY] Context building failed: %s", e)
            return ""


    def check_usage_patterns(self, llm_router) -> None:
        try:
            from jarvis_os.core.usage import get_usage_summary
            usage = get_usage_summary()
            
            # Simple heuristic: check if daily history has a pattern
            today_str = datetime.now().strftime("%Y-%m-%d")
            daily = usage.get("daily_history", {}).get(today_str, {})
            
            if not daily:
                return
                
            most_used = max(daily, key=daily.get)
            count = daily[most_used]
            
            if count >= 10:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM knowledge WHERE category = 'observation' AND date(created_at) = date('now')")
                    if cursor.fetchone()[0] == 0:
                        obs = f"User has heavily used the '{most_used}' feature ({count} times) today."
                        self.store_knowledge(obs, llm_router, force_category="observation")
        except Exception as e:
            logger.error("[MEMORY] Pattern checking failed: %s", e)

    def get_todays_relevant_memories(self) -> List[str]:
        try:
            today_mmdd = datetime.now().strftime("%m-%d")
            tomorrow_mmdd = (datetime.now() + timedelta(days=1)).strftime("%m-%d")
            today_str = datetime.now().strftime("%Y-%m-%d")
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            results = []
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT content FROM knowledge WHERE date_reference IN (?, ?, 'today', 'tomorrow') AND category != 'observation'",
                    (today_mmdd, tomorrow_mmdd)
                )
                rows = cursor.fetchall()
                for row in rows:
                    results.append(f"[CONTEXTUAL AWARENESS] Note: {row[0]}. If natural, you may bring this up conversationally, but only if it fits — do not force it.")

                # Callback Threading
                cursor.execute(
                    "SELECT id, content FROM knowledge WHERE date_reference IN (?, ?, 'today', 'yesterday') AND followed_up = 0",
                    (today_str, yesterday_str)
                )
                rows = cursor.fetchall()
                keywords = ['tomorrow', 'nervous', 'worried', 'hoping', 'interview', 'demo', 'deadline', 'exam']
                
                for row_id, content in rows:
                    if any(kw in content.lower() for kw in keywords):
                        results.append(f"[FOLLOW-UP OPPORTUNITY] User mentioned: {content}. If it feels natural in conversation, you may ask how it went — but only once, and only if not already asked.")
                        cursor.execute("UPDATE knowledge SET followed_up = 1 WHERE id = ?", (row_id,))
                        conn.commit()

                # Pattern Noticing
                cursor.execute(
                    "SELECT id, content FROM knowledge WHERE category = 'observation' AND date(created_at) = date('now') AND followed_up = 0 LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    results.append(f"[OBSERVATION] {row[1]}. You may mention this casually if it fits.")
                    cursor.execute("UPDATE knowledge SET followed_up = 1 WHERE id = ?", (row[0],))
                    conn.commit()

            return results
        except Exception as e:
            logger.error("[MEMORY] Failed to get today's memories: %s", e)
            return []

    def extract_passive_knowledge(self, message: str, llm_router) -> None:
        """Runs in background: extracts facts passively without user asking 'remember'."""
        if len(message) < 10 or len(message) > 500:
            return
            
        prompt = (
            "Does the following user message state a clear, permanent personal fact, preference, "
            "procedural rule, or a date-related life event (e.g., birthday, anniversary, important calendar date, deadline) about the user? "
            "(Ignore casual chat, opinions on current events, or temporary statuses).\n"
            "If YES, output the extracted fact as a clean, standalone sentence.\n"
            "If the fact contains a date or time reference (like 'July 25', 'tomorrow', 'next Monday'), "
            "also output a '|' followed by a normalized 'MM-DD' or 'YYYY-MM-DD' representation of the date, or 'tomorrow'.\n"
            "Example output 1: The user is allergic to peanuts.\n"
            "Example output 2: The user's birthday is on July 25.|07-25\n"
            "If NO, output exactly 'null'.\n\n"
            f"Message: {message}"
        )
        
        try:
            resp = llm_router.get_response(prompt).strip()
            if resp.lower() != 'null' and len(resp) > 5:
                # Check for date reference
                date_ref = None
                if '|' in resp:
                    fact, date_ref = resp.split('|', 1)
                    resp = fact.strip()
                    date_ref = date_ref.strip()
                
                logger.info(f"[MEMORY] Passive Fact Extracted: {resp} (Date: {date_ref})")
                self.store_knowledge(resp, llm_router, date_reference=date_ref)
        except Exception as e:
            logger.debug(f"[MEMORY] Passive extraction failed silently: {e}")

if __name__ == "__main__":
    def test_redaction():
        ms = MemoryService()
        from app.utils.redact import redact_text
        res = redact_text('my card is 4111 1111 1111 1111')
        assert res == 'my card is [REDACTED_CARD]', f"Got {res}"
        print("Test passed!")
    
    test_redaction()
