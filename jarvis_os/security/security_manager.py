from jarvis_os.security.security_rules import SecurityRules
from jarvis_os.security.security_audit import SecurityAudit

class SecurityManager:
    """
    Global Security Coordinator.
    All future abilities (Desktop, Browser, Phone) MUST pass through here.
    """
    def __init__(self):
        self.rules = SecurityRules()
        self.audit = SecurityAudit()
        
    def validate_path(self, path: str) -> bool:
        return self.rules.is_path_safe(path)
        
    def log_action(self, request: str, decision: str, approval: str, execution: str, result: str):
        self.audit.log_event(request, decision, approval, execution, result)
