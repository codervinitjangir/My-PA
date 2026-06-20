from typing import List, Optional
from jarvis_os.decision.decision_models import DecisionCandidate, Decision

class DecisionSelector:
    """
    Selects a single decision from a list of candidates.
    """
    def _priority_score(self, priority: str) -> int:
        mapping = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return mapping.get(priority.lower(), 0)

    def select(self, candidates: List[DecisionCandidate]) -> Optional[Decision]:
        if not candidates:
            return None
            
        # Sort by priority, then by confidence
        sorted_candidates = sorted(
            candidates, 
            key=lambda c: (self._priority_score(c.priority), c.confidence), 
            reverse=True
        )
        
        top_candidate = sorted_candidates[0]
        
        return Decision(
            id=top_candidate.id,
            category=top_candidate.category,
            title=top_candidate.title,
            description=top_candidate.description,
            priority=top_candidate.priority,
            confidence=top_candidate.confidence,
            reason=top_candidate.reason
        )
