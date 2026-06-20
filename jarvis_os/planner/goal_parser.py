from jarvis_os.planner.planner_models import Goal

class GoalParser:
    """
    Parses natural language into a structured Goal object.
    Currently uses simple rule-based extraction (no AI).
    """
    def parse(self, natural_language_input: str) -> Goal:
        # Simple rule-based extraction
        title = natural_language_input.strip()
        description = f"User requested: '{natural_language_input}'"
        
        # Clean common prefixes
        prefixes_to_remove = ["help me", "i want to", "can you", "please"]
        lower_input = title.lower()
        for prefix in prefixes_to_remove:
            if lower_input.startswith(prefix):
                title = title[len(prefix):].strip().capitalize()
                break
                
        return Goal(
            title=title if title else "Unspecified Goal",
            description=description
        )
