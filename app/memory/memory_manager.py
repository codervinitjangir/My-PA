import logging
from typing import Dict, Any
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("J.A.R.V.I.S")

class MemoryManager:
    """
    Manages partitioned memory for JARVIS.
    Wraps the VectorStoreService and adds logical partitions for profiles and projects.
    """
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        self.partitions = {
            "user_profile": {},
            "projects": {},
            "preferences": {}
        }
        
    def _redact_pii(self, text: str) -> str:
        """
        Locally redacts sensitive information before it hits the vector database.
        Pattern mapped from ISAIR's privacy-first design.
        """
        import re
        # Basic email redaction
        text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', text)
        # Basic credit card / phone number structure redaction
        text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CC_REDACTED]', text)
        return text
        
    def add_to_long_term(self, text: str, metadata: dict = None):
        """Adds information to the vector database for long-term retention."""
        safe_text = self._redact_pii(text)
        self.vector_store.add_texts([safe_text], [metadata] if metadata else None)
        logger.info("[MEMORY] Added redacted item to long-term memory.")
        
    def get_context(self, query: str, k: int = 5) -> str:
        """Retrieves relevant context from the vector database."""
        try:
            retriever = self.vector_store.get_retriever(k=k)
            docs = retriever.invoke(query)
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            logger.warning(f"[MEMORY] Context retrieval failed: {e}")
            return ""
            
    def update_profile(self, key: str, value: Any):
        """Updates the short-term or session-based user profile partition."""
        self.partitions["user_profile"][key] = value
        logger.info(f"[MEMORY] Updated user profile: {key}")
