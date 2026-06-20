import os
import platform
import webbrowser
from jarvis_os.core.quick_links import SITE_MAP

class OSAdapter:
    """
    Cross-platform execution bridge.
    Strictly NO SUBPROCESS usage anywhere.
    """
    def execute(self, target_path: str) -> bool:
        sys_os = platform.system()
        
        if sys_os == "Windows":
            try:
                # Handle URLs (aliases) first
                if target_path in SITE_MAP:
                    webbrowser.open(SITE_MAP[target_path])
                    return True
                    
                os.startfile(target_path)
                return True
            except Exception:
                return False
        elif sys_os == "Linux":
            # TODO: Implement safe Linux execution without subprocess.run
            # Cannot use xdg-open via subprocess per strict rules.
            return False
        elif sys_os == "Darwin":
            # TODO: Implement safe macOS execution without subprocess.run
            # Cannot use open via subprocess per strict rules.
            return False
            
        return False
