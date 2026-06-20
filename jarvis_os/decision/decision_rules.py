from typing import List
from jarvis_os.decision.decision_models import DecisionCandidate, DecisionContext, DecisionCategory

class DecisionRules:
    """
    Deterministic rule sets to evaluate what should happen next.
    """
    def apply_rules(self, context: DecisionContext) -> List[DecisionCandidate]:
        candidates = []
        
        # Rule 1: If memory is obsolete, ignore
        # (This is simplified; assuming filter removed obsolete, but if any slip through)
        
        # Rule 2: If interview tomorrow -> increase urgency
        # We check memories for 'interview' and 'tomorrow'
        has_interview = any("interview" in m.get("content", "").lower() for m in context.memory)
        
        # Rule 3: If active goal exists -> prioritize active goal
        if context.active_goals:
            candidates.append(DecisionCandidate(
                category=DecisionCategory.PLAN,
                title="Work on Active Goal",
                description=f"Active goal detected: {context.active_goals[0]}",
                priority="high" if has_interview else "medium",
                confidence=0.9,
                reason="Active goals should be prioritized."
            ))
            
        # Rule 4: If current focus = coding -> avoid interruptions
        if context.current_focus.lower() == "coding":
            candidates.append(DecisionCandidate(
                category=DecisionCategory.WAIT,
                title="Avoid Interruption",
                description="User is coding.",
                priority="high",
                confidence=1.0,
                reason="Current focus is coding; avoid interrupting."
            ))
            
        # Default fallback
        if not candidates:
            candidates.append(DecisionCandidate(
                category=DecisionCategory.OBSERVE,
                title="Passively Observe",
                description="No immediate action required.",
                priority="low",
                confidence=0.8,
                reason="No active rules triggered."
            ))
            
        return candidates
