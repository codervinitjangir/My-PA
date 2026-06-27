from app.tools.base_tool import BaseTool
from pathlib import Path
import os

SEARCH_DIRS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Documents",
]

class FileFinderTool(BaseTool):
    name: str = "file_finder"
    description: str = "Find a file by name or type on the local filesystem and return its path."

    def execute(self, filename: str = None, file_type: str = None, **kwargs) -> dict:
        """
        Search SEARCH_DIRS for a file matching filename (partial match ok)
        or file_type extension (e.g. "pdf").
        Returns: {"found": True, "path": "/full/path/to/file.pdf", "filename": "file.pdf", "size_mb": 1.2}
        or {"found": False, "error": "No matching file found"}

        Search is case-insensitive. If multiple matches, return the most recently modified.
        """
        best_match = None
        best_mtime = -1

        target_name = filename.lower() if filename else None
        target_ext = f".{file_type.lower()}" if file_type else None

        for search_dir in SEARCH_DIRS:
            if not search_dir.exists():
                continue
                
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    file_lower = file.lower()
                    match = False
                    
                    if target_name and target_name in file_lower:
                        match = True
                    elif target_ext and file_lower.endswith(target_ext):
                        match = True
                        
                    if match:
                        full_path = Path(root) / file
                        try:
                            mtime = full_path.stat().st_mtime
                            if mtime > best_mtime:
                                best_mtime = mtime
                                best_match = full_path
                        except Exception:
                            pass

        if best_match:
            try:
                size_mb = best_match.stat().st_size / (1024 * 1024)
                return {
                    "found": True,
                    "path": str(best_match),
                    "filename": best_match.name,
                    "size_mb": size_mb
                }
            except Exception as e:
                return {"found": False, "error": str(e)}

        return {"found": False, "error": "No matching file found"}

from app.tools.registry import ToolRegistry
ToolRegistry.register(FileFinderTool())
