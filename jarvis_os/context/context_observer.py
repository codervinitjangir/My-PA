from typing import List

class ContextObserver:
    """
    Passively observes new events (memories, goals, projects).
    Does NOT execute actions.
    """
    def __init__(self):
        self.observed_events = []

    def observe(self, event_type: str, data: any):
        """
        Record a new event observation.
        event_type examples: 'new_memory', 'new_goal', 'new_project'
        """
        self.observed_events.append({"type": event_type, "data": data})

    def get_recent_observations(self) -> List[dict]:
        return self.observed_events[-5:]
