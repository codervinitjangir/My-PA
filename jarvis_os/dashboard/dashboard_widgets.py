def timeline_widget(global_state: dict) -> dict:
    """
    Sub-50ms deterministic timeline widget data.
    Extracts streak, progress, and pending from global state.
    """
    pending = global_state.get("pending_items", 0)
    
    # Mock data to simulate session parsing for this sprint
    # In a full integration, this reads from jarvis_os/session/ history logs
    completed_today = 3
    streak = 5
    milestones = []
    
    total = completed_today + pending
    progress_percentage = int((completed_today / total) * 100) if total > 0 else 0
    
    if streak >= 5:
        milestones.append("🔥 5-Day Streak!")
        
    return {
        "yesterday_summary": {
            "completed": ["Jarvis Dashboard", "Daily Brief"],
            "pending": ["Timeline Widget"]
        },
        "metrics": {
            "current_streak": streak,
            "completed_count": completed_today,
            "pending_count": pending,
            "progress_percentage": progress_percentage,
            "milestones": milestones
        }
    }
