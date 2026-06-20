from typing import List
from jarvis_os.verifier.verification_models import VerificationResult

class VerificationHistory:
    """
    Maintains a log of verification outcomes.
    """
    def __init__(self):
        self.history: List[VerificationResult] = []
        
    def log_result(self, result: VerificationResult):
        self.history.append(result)
        
    def get_history(self) -> List[VerificationResult]:
        return self.history
