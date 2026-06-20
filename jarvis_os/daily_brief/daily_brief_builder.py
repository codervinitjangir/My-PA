from datetime import datetime
from jarvis_os.daily_brief.daily_brief_models import BriefingState

class DailyBriefBuilder:
    def build_state(self, global_state: dict) -> BriefingState:
        hour = datetime.now().hour
        
        # 1. Time Logic
        if hour >= 5 and hour < 12:
            greeting = "Good Morning Boss. Here is your daily briefing."
        elif hour >= 12 and hour < 17:
            greeting = "Good Afternoon Boss. Here is your mid-day status."
        else:
            greeting = "Good Evening Boss. Here is your end-of-day summary."
            
        # Extract variables
        comp_state = global_state.get("computer_state", {})
        cpu_usage_str = comp_state.get("cpu_usage", "0%").strip("%")
        ram_usage_str = comp_state.get("memory_usage", "0%").strip("%")
        
        try:
            cpu_val = float(cpu_usage_str)
            ram_val = float(ram_usage_str)
        except ValueError:
            cpu_val = 0.0
            ram_val = 0.0
            
        pending = global_state.get("pending_items", 0)
        focus = global_state.get("current_focus", "").lower()
        active_proj = global_state.get("active_project", "")
        
        # 2. Energy Score
        if cpu_val < 50 and ram_val < 60:
            energy_score = "High"
        elif cpu_val < 80 and ram_val < 85:
            energy_score = "Medium"
        else:
            energy_score = "Low"
            
        # 3. Today Mode
        if pending == 0 and not active_proj:
            today_mode = "😴 Light Day"
        elif pending > 5:
            today_mode = "💼 Work"
        elif "learn" in focus or "research" in focus:
            today_mode = "📚 Learn"
        elif active_proj:
            today_mode = "🚀 Build"
        else:
            today_mode = "🛠️ Maintenance"
            
        # 4. Suggested Action
        if "jarvis" in active_proj.lower():
            suggested_action = "Continue Jarvis"
        elif today_mode == "🚀 Build":
            suggested_action = "Open VS Code"
        elif pending > 3:
            suggested_action = "Show Pending Tasks"
        else:
            suggested_action = "Check Active Session"
            
        computer_status = f"All systems nominal. CPU: {cpu_val}%, RAM: {ram_val}%."
        
        return BriefingState(
            greeting=greeting,
            today_focus=global_state.get("current_focus", "No focus set"),
            active_projects=[active_proj] if active_proj else [],
            pending_tasks=pending,
            recommendations=global_state.get("recommendations", []),
            computer_status=computer_status,
            suggested_action=suggested_action,
            energy_score=energy_score,
            today_mode=today_mode
        )
