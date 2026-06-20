from typing import List
from jarvis_os.runtime.runtime_state import RuntimeState

class RuntimeContext:
    def __init__(self):
        self.state = RuntimeState()
        
    def get_top_memories(self) -> List[str]:
        # Simulated memories retrieval
        return [
            "User requested that BrainService remain untouched and lightweight.",
            "Maximum context injection limit is 500 words to ensure optimal token safety.",
            "RealtimeService and GroqService are the primary generative AI injection points."
        ]
        
    def compile_compact_context(self) -> str:
        """
        Compiles the prioritized state variables into a compact string representation.
        Max 400-500 words target.
        """
        lines = ["<jarvis_os_context>"]
        
        lines.append(f"  <current_focus>{self.state.current_focus}</current_focus>")
        
        lines.append("  <active_goals>")
        for goal in self.state.active_goals:
            lines.append(f"    - {goal}")
        lines.append("  </active_goals>")
        
        lines.append("  <active_projects>")
        for proj in self.state.active_projects:
            lines.append(f"    - {proj}")
        lines.append("  </active_projects>")
        
        lines.append("  <top_memories>")
        for memory in self.get_top_memories():
            lines.append(f"    - {memory}")
        lines.append("  </top_memories>")
        
        lines.append("  <current_priorities>")
        for priority in self.state.current_priorities:
            lines.append(f"    - {priority}")
        lines.append("  </current_priorities>")
        
        lines.append("</jarvis_os_context>")
        
        return "\n".join(lines)
