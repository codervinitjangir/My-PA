import re
from typing import List

class ContextBuilder:
    """
    Constructs the final aware context object, including current focus.
    """
    def build_current_context(self, identity: dict, projects: list, goals: list, memories: list, devices: dict, session: dict, priority_items: list) -> dict:
        return {
            "identity": identity,
            "active_projects": projects,
            "active_goals": goals,
            "current_focus": self.detect_current_focus(session),
            "recent_memories": memories,
            "important_memories": priority_items,
            "priority_items": priority_items,
            "device_status": devices,
            "session_context": session
        }

    def detect_current_focus(self, session: dict) -> str:
        """
        Simple heuristic focus detection based on frequency of words in recent messages.
        """
        history = session.get("history", [])
        if not history:
            return "general"
            
        text_content = " ".join([msg.get("content", "").lower() for msg in history[-5:]])
        
        if "jarvis" in text_content:
            return "Jarvis System"
        if "internship" in text_content or "interview" in text_content:
            return "Career / Internships"
        if "code" in text_content or "bug" in text_content or "python" in text_content:
            return "Coding"
            
        return "general"
