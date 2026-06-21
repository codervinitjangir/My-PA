import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("J.A.R.V.I.S")

class UserProfileManager:
    """
    Manages explicit, high-priority user facts (Name, preferences)
    so they are never lost in semantic search thresholds.
    """
    def __init__(self, profile_path: str = "chats/user_profile.json"):
        self.profile_path = Path(profile_path)
        self._ensure_file()
        self.profile: Dict[str, Any] = self._load()

    def _ensure_file(self):
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.profile_path.exists():
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump({"name": "User", "preferences": []}, f)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[USER_PROFILE] Failed to load: {e}")
            return {}

    def save(self):
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=4)
        except Exception as e:
            logger.error(f"[USER_PROFILE] Failed to save: {e}")

    def update_preference(self, pref: str):
        if "preferences" not in self.profile:
            self.profile["preferences"] = []
        if pref not in self.profile["preferences"]:
            self.profile["preferences"].append(pref)
            self.save()
            
    def get_profile_summary(self) -> str:
        name = self.profile.get("name", "User")
        prefs = self.profile.get("preferences", [])
        pref_str = ", ".join(prefs) if prefs else "None known yet."
        return f"User Name: {name}\nUser Preferences: {pref_str}"
