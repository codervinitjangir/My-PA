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
        
    def add_to_long_term(self, text: str, metadata: dict = None):
        """Adds information to the vector database for long-term retention."""
        self.vector_store.add_texts([text], [metadata] if metadata else None)
        logger.info("[MEMORY] Added item to long-term memory.")
        
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
