from jarvis_os.security.security_manager import SecurityManager
from jarvis_os.core.quick_links import SITE_MAP

class SafetyLock:
    """
    The absolute firewall for desktop actions.
    Enforces the whitelist and delegates to SecurityManager for path validation.
    """
    WHITELISTED_ACTIONS = ["open_application", "open_folder", "open_file", "open_site"]
    
    def __init__(self):
        self.security = SecurityManager()
        
    def check_safety(self, action: str, target: str) -> bool:
        if action not in self.WHITELISTED_ACTIONS:
            return False
            
        if not target or target.strip() == "":
            return False
            
        if action == "open_site":
            if target not in SITE_MAP:
                return False
            return True
            
        if not self.security.validate_path(target):
            return False
            
        return True
