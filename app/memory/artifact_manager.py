import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("J.A.R.V.I.S")

class ArtifactManager:
    """
    Persistent Key-Value store for exact-match tracking (Journals, Lists, Settings).
    Complements the Vector Database by ensuring 100% recall accuracy for structured data.
    """
    def __init__(self, db_path: str = "chats/artifacts.json"):
        self.db_path = Path(db_path)
        self._ensure_db()
        self.artifacts: Dict[str, Any] = self._load()

    def _ensure_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ARTIFACT_DB] Failed to load artifacts: {e}")
            return {}

    def _save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.artifacts, f, indent=4)
        except Exception as e:
            logger.error(f"[ARTIFACT_DB] Failed to save artifacts: {e}")

    def upsert(self, key: str, value: Any) -> bool:
        """Add or update an artifact."""
        self.artifacts[key] = value
        self._save()
        logger.info(f"[ARTIFACT_DB] Upserted key: {key}")
        return True

    def get(self, key: str) -> Any:
        """Retrieve an artifact by key."""
        return self.artifacts.get(key)
        
    def delete(self, key: str) -> bool:
        """Delete an artifact by key."""
        if key in self.artifacts:
            del self.artifacts[key]
            self._save()
            return True
        return False
        
    def list_keys(self) -> list:
        return list(self.artifacts.keys())
