import logging
from app.tools.base_tool import BaseTool
from app.memory.artifact_manager import ArtifactManager

logger = logging.getLogger("J.A.R.V.I.S")
artifact_manager = ArtifactManager()

class ArtifactTool(BaseTool):
    name = "manage_artifact"
    description = "Manages persistent Key-Value artifacts (journals, lists). Actions: 'upsert', 'get', 'delete', 'list'."
    
    def execute(self, action: str, key: str = None, value: str = None, **kwargs) -> dict:
        logger.info(f"[ARTIFACT] Action: {action} | Key: {key}")
        
        if action == "upsert" and key and value:
            artifact_manager.upsert(key, value)
            return {"status": "success", "message": f"Artifact '{key}' saved."}
            
        elif action == "get" and key:
            val = artifact_manager.get(key)
            if val is not None:
                return {"status": "success", "value": val}
            return {"status": "error", "message": f"Artifact '{key}' not found."}
            
        elif action == "delete" and key:
            if artifact_manager.delete(key):
                return {"status": "success", "message": f"Artifact '{key}' deleted."}
            return {"status": "error", "message": f"Artifact '{key}' not found."}
            
        elif action == "list":
            return {"status": "success", "keys": artifact_manager.list_keys()}
            
        return {"status": "error", "message": "Invalid action or missing parameters."}
