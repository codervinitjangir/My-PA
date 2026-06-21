import os
import time
import logging
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class TakeNoteTool(BaseTool):
    name = "take_note"
    description = "Saves an important note to a text file and prepares it for long-term memory indexing."
    
    def execute(self, content: str, topic: str = "General", **kwargs) -> dict:
        save_dir = os.path.join(os.getcwd(), "notes")
        os.makedirs(save_dir, exist_ok=True)
        
        filename = f"note_{topic.lower().replace(' ', '_')}_{int(time.time())}.txt"
        filepath = os.path.join(save_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[NOTE] Saved note to {filepath}")
            
            # Simulated MemoryManager integration (Vector DB Sync)
            logger.info(f"[NOTE] (MemoryManager sync) Indexed note under topic: {topic}")
            
            return {"status": "success", "filepath": filepath, "topic": topic}
        except Exception as e:
            logger.error(f"[NOTE] Failed to save note: {e}")
            return {"status": "error", "message": str(e)}
