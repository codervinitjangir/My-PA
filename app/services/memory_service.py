import sqlite3
import logging
import threading
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

logger = logging.getLogger("J.A.R.V.I.S.Memory")

class MemoryService:
    def __init__(self, db_path: str = "database/jarvis_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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

    def maybe_summarise(self, session_id: str, messages: List[any], llm_router) -> None:
        if not messages or len(messages) < 15 or len(messages) % 15 != 0:
            return
            
        logger.info("[MEMORY] Triggering background summary for session %s (msgs: %d)", session_id, len(messages))
        
        try:
            # Format history for prompt
            history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages[-15:]])
            
            prompt = (
                "You are JARVIS. Summarise the following recent conversation into EXACTLY "
                "one concise paragraph (max 150 words). Capture key context, facts, and state. "
                "Do NOT include conversational filler.\n\n"
                f"Conversation:\n{history_text}"
            )
            
            # Using the router to get response (benefits from fallback chain)
            summary = llm_router.get_response(prompt)
            
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO summaries (session_id, summary) VALUES (?, ?)", 
                    (session_id, summary.strip())
                )
                conn.commit()
                logger.info("[MEMORY] Saved session summary")
                
        except Exception as e:
            logger.error("[MEMORY] Summarisation failed: %s", e)

    def store_knowledge(self, content: str, llm_router) -> str:
        try:
            prompt = (
                "Categorize the following information into exactly ONE of these categories: "
                "preference, project, person, decision, fact.\n"
                "Return ONLY the category name in lowercase, nothing else.\n"
                f"Information: {content}"
            )
            category = llm_router.get_response(prompt).strip().lower()
            
            valid_cats = ["preference", "project", "person", "decision", "fact"]
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
                    cursor.execute(
                        "UPDATE knowledge SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (content, best_match_id)
                    )
                    conn.commit()
                    return f"Updated existing {category} memory."
                else:
                    cursor.execute(
                        "INSERT INTO knowledge (content, category) VALUES (?, ?)",
                        (content, category)
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

    def build_memory_context(self, session_id: str, query: str) -> str:
        try:
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

