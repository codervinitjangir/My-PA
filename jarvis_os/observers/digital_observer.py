import time
from typing import List, Optional
from jarvis_os.observers.observer_models import DigitalActivity, ActivityType

class DigitalObserver:
    """
    Read-only observer that infers Digital Activity from passive signals.
    Execution time must be < 50ms, using strict deterministic rules (No LLM).
    """

    def __init__(self):
        self.rules = [
            # Building
            (ActivityType.BUILDING, ["Code.exe", "VS Code", "PyCharm"], ["github.com", "stackoverflow.com", "localhost"]),
            # Job Search
            (ActivityType.JOB_SEARCH, [], ["linkedin.com", "indeed.com", "glassdoor.com"]),
            # Learning
            (ActivityType.LEARNING, [], ["docs", "documentation", "leetcode.com", "coursera.org", "tutorial"]),
            # Research
            (ActivityType.RESEARCH, [], ["chatgpt.com", "claude.ai", "arxiv.org", "wikipedia.org", "research"]),
            # Entertainment
            (ActivityType.ENTERTAINMENT, ["Spotify", "Steam"], ["youtube.com", "netflix.com", "twitch.tv"]),
            # Communication
            (ActivityType.COMMUNICATION, ["Slack", "Discord", "Teams.exe"], ["gmail.com", "mail"]),
            # Social
            (ActivityType.SOCIAL, [], ["twitter.com", "x.com", "facebook.com", "instagram.com", "reddit.com"]),
        ]

    def observe(self, 
                active_window_title: str, 
                browser_name: Optional[str], 
                running_processes: List[str], 
                active_session: Optional[str], 
                active_project: Optional[str]) -> DigitalActivity:
        """
        Infers the current activity based on signals and detects focus drift.
        """
        start_time = time.time()
        
        # 1. Infer Activity
        inferred_activity = ActivityType.UNKNOWN
        confidence = 0.1
        title_lower = active_window_title.lower() if active_window_title else ""
        
        for activity_enum, process_keywords, window_keywords in self.rules:
            # Check if active window matches keywords
            for kw in window_keywords:
                if kw.lower() in title_lower:
                    inferred_activity = activity_enum
                    confidence = 0.8
                    break
            if inferred_activity != ActivityType.UNKNOWN:
                break
                
            # Check running processes if active window didn't yield a definitive match
            for kw in process_keywords:
                for proc in running_processes:
                    if kw.lower() in proc.lower():
                        inferred_activity = activity_enum
                        confidence = 0.5
                        break
                if inferred_activity != ActivityType.UNKNOWN:
                    break
                    
            if inferred_activity != ActivityType.UNKNOWN:
                break
                
        # Additional context-based override
        if inferred_activity == ActivityType.UNKNOWN and active_project:
            inferred_activity = ActivityType.BUILDING
            confidence = 0.4
            
        # 2. Detect Focus Drift
        focus_drift = False
        
        # If we have an active session/project but we're doing entertainment/social, that's a drift
        distracting_activities = [ActivityType.ENTERTAINMENT, ActivityType.SOCIAL]
        working_contexts = [ActivityType.BUILDING, ActivityType.LEARNING, ActivityType.RESEARCH]
        
        if active_session or active_project:
            if inferred_activity in distracting_activities:
                focus_drift = True
            elif inferred_activity == ActivityType.UNKNOWN and ("youtube" in title_lower or "reddit" in title_lower):
                 focus_drift = True
                 inferred_activity = ActivityType.ENTERTAINMENT

        # Enforce <50ms performance rule
        execution_time = (time.time() - start_time) * 1000
        if execution_time > 50:
            pass # In a real scenario we might log a warning
            
        return DigitalActivity(
            activity=inferred_activity,
            confidence=confidence,
            source="DigitalObserver",
            timestamp=time.time(),
            focus_drift=focus_drift
        )
