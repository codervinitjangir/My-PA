import logging
from typing import List, Dict, Any

logger = logging.getLogger("J.A.R.V.I.S")

class MemoryManager:
    """
    Handles Short-term (session) and Long-term (vector) memory context injection.
    """
    def __init__(self, vector_store_service=None):
        self.vector_store_service = vector_store_service
        self.short_term_memory: Dict[str, List[Dict[str, str]]] = {}

    def inject_context(self, session_id: str, query: str) -> str:
        """
        Retrieves relevant context for a given query and prepends it.
        """
        context = []
        
        # 1. Fetch from Vector Store (Long-term)
        if self.vector_store_service and hasattr(self.vector_store_service, 'search'):
            try:
                docs = self.vector_store_service.search(query, top_k=3)
                if docs:
                    context.append("Relevant Past Knowledge:\n" + "\n".join(docs))
            except Exception as e:
                logger.warning(f"[MemoryManager] Vector fetch failed: {e}")

        # 2. Basic OS Profile (Phase 1)
        context.append("System Context: You are running as a Personal AI OS.")

        if context:
            combined = "\n\n".join(context)
            return f"--- OS MEMORY CONTEXT ---\n{combined}\n-------------------------\n\nUser Query: {query}"
        
        return query
