import logging
import io
import os
import sys
import contextlib
from pathlib import Path
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

WORKSPACE_DIR = Path(os.getcwd()) / "app" / "workspace"

class PythonExecutionTool(BaseTool):
    name = "execute_python"
    description = "Executes pure Python code dynamically and returns stdout. The code runs inside the app/workspace/ sandbox directory, so you can safely read/write files there."
    
    def execute(self, code: str, **kwargs) -> dict:
        logger.info("[PYTHON_EXEC] Executing dynamic code snippet")
        
        # Ensure workspace exists
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Capture stdout
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        local_scope = {}
        old_cwd = os.getcwd()
        try:
            # Sandbox cwd
            os.chdir(WORKSPACE_DIR)
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code, {"__builtins__": __builtins__}, local_scope)
            
            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()
            
            if errors:
                return {"status": "success_with_stderr", "output": output, "stderr": errors}
                
            return {"status": "success", "output": output}
        except Exception as e:
            logger.error(f"[PYTHON_EXEC] Code execution failed: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            os.chdir(old_cwd)
