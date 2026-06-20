class BrainAdapter:
    """
    Wrapper for the eventual AI backend (e.g., brain_service.py).
    Prepares a compact string package of context before every AI request.
    """
    
    def build_ai_context(self, jarvis_state: dict) -> str:
        """
        Builds a concise string (max 1000 words) for injection into system prompts.
        """
        identity = jarvis_state.get("identity", {})
        boss_name = identity.get("name", "Boss")
        current_focus = jarvis_state.get("current_focus", "general")
        
        active_projects = jarvis_state.get("active_projects", [])
        active_projects_str = "\n".join([f"* {p}" for p in active_projects]) if active_projects else "* None"
        
        goals = jarvis_state.get("active_goals", [])
        goals_str = "\n".join([f"* {g}" for g in goals]) if goals else "* None"
        
        memories = jarvis_state.get("important_memories", [])
        memories_str = "\n".join([f"* {m.get('content')}" for m in memories]) if memories else "* None"
        
        ai_context = (
            f"Boss: {boss_name}\n"
            f"Current Focus: {current_focus}\n\n"
            f"Active Projects:\n{active_projects_str}\n\n"
            f"Goals:\n{goals_str}\n\n"
            f"Recent Important Memories:\n{memories_str}"
        )
        
        # Ensure it is concise (basic word count check)
        words = ai_context.split()
        if len(words) > 800:
            ai_context = " ".join(words[:800]) + "...\n(Context truncated to save tokens)"
            
        return ai_context
