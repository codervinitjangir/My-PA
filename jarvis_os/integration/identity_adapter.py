from jarvis_os.identity.identity_manager import IdentityManager

class IdentityAdapter:
    """
    Adapter bridging the Identity Engine to the Integration Layer.
    """
    def __init__(self, identity_manager: IdentityManager):
        self.manager = identity_manager

    def get_core_identity(self) -> dict:
        context = self.manager.get_identity_context()
        return {
            "name": context.get("name", "Boss"),
            "active_projects": [p.get("project_name") for p in context.get("projects", []) if p.get("status") == "active"][:3],
            "active_goals": context.get("goals", {}).get("active_goals", [])[:3],
            "preferences": context.get("preferences", {})
        }
