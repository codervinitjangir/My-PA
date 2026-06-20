import json
import os
from jarvis_os.shared.constants import PROFILES_DIR, IDENTITY_FILES
from jarvis_os.shared.types import IdentityDict
import logging

logger = logging.getLogger(__name__)

class IdentityLoader:
    def __init__(self):
        self.profiles_dir = PROFILES_DIR

    def _load_json(self, filename: str) -> IdentityDict:
        filepath = os.path.join(self.profiles_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Identity file not found: {filepath}")
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {str(e)}")
            return {}

    def load_all(self) -> IdentityDict:
        return {
            "profile": self._load_json(IDENTITY_FILES["profile"]),
            "preferences": self._load_json(IDENTITY_FILES["preferences"]),
            "devices": self._load_json(IDENTITY_FILES["devices"]),
            "goals": self._load_json(IDENTITY_FILES["goals"]),
            "projects": self._load_json(IDENTITY_FILES["projects"]),
            "relationships": self._load_json(IDENTITY_FILES["relationships"])
        }
