import logging
import time
from pathlib import Path
from app.tools.base_tool import BaseTool
from app.services.vector_store import VectorStoreService
from app.memory.user_profile_manager import UserProfileManager

logger = logging.getLogger("J.A.R.V.I.S")

# Assuming singleton-like access for prototype
vector_store_service = VectorStoreService()
user_profile_manager = UserProfileManager()

class SupermemoryTool(BaseTool):
    name = "supermemory"
    description = "Active memory API. Actions: 'save' (saves a note/fact to long-term vector memory), 'recall' (searches memory and returns matches + user profile)."
    
    def execute(self, action: str, data: str, **kwargs) -> dict:
        logger.info(f"[SUPERMEMORY] Action: {action}")
        
        if action == "save":
            try:
                learning_dir = Path("learning_data")
                learning_dir.mkdir(exist_ok=True)
                with open(learning_dir / "explicit_memory.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n--- [TS:{int(time.time())}] EXPLICIT FACT ---\n{data}\n")
                return {"status": "success", "message": "Memory explicitly saved to vector ingestion queue."}
            except Exception as e:
                return {"status": "error", "message": f"Failed to save: {e}"}
                
        elif action == "recall":
            try:
                # Need to load/build vector store if not done
                if not vector_store_service.vector_store:
                    vector_store_service.create_vector_store()
                    
                docs = vector_store_service.search_with_temporal_bias(data, k=3)
                results = [d.page_content for d in docs] if docs else ["No memory found."]
                
                profile = user_profile_manager.get_profile_summary()
                
                return {
                    "status": "success",
                    "profile_context": profile,
                    "memory_matches": results
                }
            except Exception as e:
                return {"status": "error", "message": f"Recall failed: {e}"}
        else:
            return {"status": "error", "message": "Invalid action. Use 'save' or 'recall'."}
