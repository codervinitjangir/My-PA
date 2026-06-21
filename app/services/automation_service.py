import logging
import threading
import time
from typing import Callable, Dict

logger = logging.getLogger("J.A.R.V.I.S")

class AutomationService:
    """
    n8n Concept: Background Workflow Automation Engine.
    Runs triggers and schedules asynchronously without blocking the UI.
    """
    def __init__(self):
        self._running = False
        self._thread = None
        self._scheduled_jobs: Dict[str, dict] = {}
        
    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("[AUTOMATION] Service started.")
            
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("[AUTOMATION] Service stopped.")

    def schedule_job(self, job_id: str, interval_seconds: int, func: Callable):
        self._scheduled_jobs[job_id] = {
            "interval": interval_seconds,
            "func": func,
            "last_run": time.time()
        }
        logger.info(f"[AUTOMATION] Scheduled job '{job_id}' every {interval_seconds}s")

    def run_in_background(self, func: Callable, *args, **kwargs):
        """Runs a one-off workflow in a detached background thread."""
        logger.info(f"[AUTOMATION] Spawning background workflow thread for {func.__name__}")
        threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True).start()

    def _run_loop(self):
        while self._running:
            now = time.time()
            for job_id, job in self._scheduled_jobs.items():
                if now - job["last_run"] >= job["interval"]:
                    logger.info(f"[AUTOMATION] Triggering scheduled job: {job_id}")
                    try:
                        job["func"]()
                    except Exception as e:
                        logger.error(f"[AUTOMATION] Job {job_id} failed: {e}")
                    finally:
                        job["last_run"] = time.time()
            time.sleep(1)

# Singleton instance
automation_service = AutomationService()
