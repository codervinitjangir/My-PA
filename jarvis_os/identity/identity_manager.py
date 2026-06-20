from jarvis_os.identity.identity_loader import IdentityLoader
from jarvis_os.shared.types import IdentityDict

class IdentityManager:
    def __init__(self):
        self.loader = IdentityLoader()
        self._cache: IdentityDict = {}
        self.load_identity()

    def load_identity(self):
        """Loads and caches the identity from disk."""
        self._cache = self.loader.load_all()

    def get_identity_context(self) -> IdentityDict:
        """
        Returns a unified context representing the user's identity.
        """
        if not self._cache:
            self.load_identity()
            
        profile = self._cache.get("profile", {})
        
        return {
            "name": profile.get("name", ""),
            "projects": self._cache.get("projects", []),
            "goals": self._cache.get("goals", {}),
            "preferences": self._cache.get("preferences", {}),
            "devices": self._cache.get("devices", [])
        }

    def update_identity(self, category: str, data: dict):
        """Updates the cached identity and eventually saves to disk."""
        pass # To be implemented in Phase 2
