from jarvis_os.planner.planner_models import Plan

class PlanPrioritizer:
    """
    Assigns a priority level (Critical, High, Medium, Low) to a Plan.
    Uses rules only.
    """
    CRITICAL_KEYWORDS = ["urgent", "emergency", "asap", "critical"]
    HIGH_KEYWORDS = ["today", "tomorrow", "important", "deadline", "interview"]
    LOW_KEYWORDS = ["someday", "later", "eventually", "no rush"]

    def prioritize(self, plan: Plan) -> Plan:
        content = f"{plan.title} {plan.description}".lower()
        
        if any(kw in content for kw in self.CRITICAL_KEYWORDS):
            plan.priority = "critical"
        elif any(kw in content for kw in self.HIGH_KEYWORDS):
            plan.priority = "high"
        elif any(kw in content for kw in self.LOW_KEYWORDS):
            plan.priority = "low"
        else:
            plan.priority = "medium"
            
        # Push priority down to tasks
        for task in plan.ordered_tasks:
            task.priority = plan.priority
            
        return plan
