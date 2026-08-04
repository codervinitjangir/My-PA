import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("J.A.R.V.I.S")

class IdentityManager:
    """
    Manages explicit, high-priority user facts (Identity, Projects, Relationships, Rules).
    Replaces basic user_profile_manager with robust categorized long-term memory.
    """
    def __init__(self, db_path: str = "database/identity.json"):
        self.db_path = Path(db_path)
        self._ensure_file()
        self.memory: Dict[str, Any] = self._load()

    def _ensure_file(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            default_state = {
                "identity": {"name": "User", "title": "Boss"},
                "preferences": [],
                "projects": {},
                "relationships": {},
                "rules": [
                    "Always refer to me by my Title.",
                    "Be highly efficient, analytical, and tactical in your responses."
                ]
            }
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(default_state, f, indent=4)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[IDENTITY] Failed to load: {e}")
            return self._get_fallback_state()

    def _get_fallback_state(self):
        return {
            "identity": {"title": "Boss"},
            "preferences": [],
            "projects": {},
            "relationships": {},
            "rules": []
        }

    def save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            logger.error(f"[IDENTITY] Failed to save: {e}")

    # --- Writers ---
    def set_identity(self, key: str, value: str):
        if "identity" not in self.memory: self.memory["identity"] = {}
        self.memory["identity"][key] = value
        self.save()

    def add_preference(self, pref: str):
        if "preferences" not in self.memory: self.memory["preferences"] = []
        if pref not in self.memory["preferences"]:
            self.memory["preferences"].append(pref)
            self.save()

    def set_project(self, project_name: str, status_or_details: str):
        if "projects" not in self.memory: self.memory["projects"] = {}
        self.memory["projects"][project_name] = status_or_details
        self.save()

    def remove_project(self, project_name: str):
        if "projects" in self.memory and project_name in self.memory["projects"]:
            del self.memory["projects"][project_name]
            self.save()

    # --- Readers ---
    def get_title(self) -> str:
        return self.memory.get("identity", {}).get("title", "Boss")

    def get_active_projects(self) -> List[str]:
        projs = self.memory.get("projects", {})
        return [f"{k}: {v}" for k, v in projs.items()]

    def get_identity_context(self) -> str:
        """Generates a compressed string of all identity facts for the LLM system prompt."""
        parts = []
        
        # 1. Identity & Title
        title = self.get_title()
        name = self.memory.get("identity", {}).get("name", "")
        parts.append(f"USER TITLE: {title}")
        if name: parts.append(f"USER NAME: {name}")

        # 2. Rules
        rules = self.memory.get("rules", [])
        if rules:
            parts.append("STRICT RULES: " + "; ".join(rules))

        # 3. Preferences
        prefs = self.memory.get("preferences", [])
        if prefs:
            parts.append("PREFERENCES: " + "; ".join(prefs))

        # 4. Projects
        projs = self.get_active_projects()
        if projs:
            parts.append("ACTIVE PROJECTS: " + " | ".join(projs))

        return "\n".join(parts)
