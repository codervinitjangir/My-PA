import os
from datetime import datetime
from jarvis_os.dashboard.dashboard_models import DashboardState, ComputerSummary

class DashboardBuilder:
    def build_state(self, global_state: dict) -> DashboardState:
        hour = datetime.now().hour
        
        if hour < 12:
            greeting = "Good Morning Boss"
            time_of_day = "morning"
        elif hour < 17:
            greeting = "Good Afternoon Boss"
            time_of_day = "afternoon"
        else:
            greeting = "Good Evening Boss"
            time_of_day = "evening"
            
        comp_state = global_state.get("computer_state", {})
        
        from jarvis_os.dashboard.dashboard_widgets import timeline_widget
        
        return DashboardState(
            greeting=greeting,
            current_focus=global_state.get("current_focus", "No focus set"),
            active_project=global_state.get("active_project", "No active project"),
            pending_items=global_state.get("pending_items", 0),
            recommendations=global_state.get("recommendations", []),
            computer_summary=ComputerSummary(
                os=comp_state.get("os", "Unknown"),
                cpu_usage=comp_state.get("cpu_usage", "0%"),
                memory_usage=comp_state.get("memory_usage", "0%")
            ),
            session_summary="Active session running",
            time_of_day=time_of_day,
            timeline=timeline_widget(global_state),
            digital_activity=global_state.get("digital_activity"),
            workspace=global_state.get("workspace"),
            current_screen=global_state.get("screen"),
            telegram_enabled=bool(os.getenv("TELEGRAM_BOT_TOKEN"))
        )
