import os
import platform

class SecurityRules:
    """
    Centralized security constraints applicable across all modules.
    """
    def get_restricted_paths(self) -> list:
        """
        Dynamically builds a list of heavily restricted root paths.
        """
        paths = []
        if platform.system() == "Windows":
            sys_root = os.environ.get("SystemRoot", "C:\\Windows")
            prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            prog_data = os.environ.get("ProgramData", "C:\\ProgramData")
            
            paths.extend([sys_root, prog_files, prog_files_x86, prog_data])
            
        return [p.lower() for p in paths]
        
    def is_path_safe(self, target_path: str) -> bool:
        if not target_path:
            return False
            
        target_lower = target_path.lower()
        for restricted in self.get_restricted_paths():
            if target_lower.startswith(restricted):
                return False
        return True

    def verify_web_action(self, action: str) -> bool:
        """
        Web Assistant strict rules. 
        Only allows stateless observing and navigating.
        """
        SAFE_WEB_ACTIONS = {"open", "search", "summarize"}
        if action not in SAFE_WEB_ACTIONS:
            raise PermissionError(f"Security Block: Web action '{action}' is strictly prohibited. Only stateless {SAFE_WEB_ACTIONS} are allowed.")
        return True
