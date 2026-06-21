import logging
from pathlib import Path
from app.connectors.local_file_connector import LocalFileConnector

logger = logging.getLogger("J.A.R.V.I.S")

class FileWatcherTrigger:
    """
    n8n Concept: Event Triggers.
    Monitors a directory and fires an action when new files arrive.
    """
    def __init__(self, watch_dir: str = "knowledge_drop"):
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(exist_ok=True)
        self.connector = LocalFileConnector()
        
    def check_for_files(self):
        """Called by the AutomationService schedule loop."""
        try:
            # Simple check for any files
            has_files = any(self.watch_dir.iterdir())
            if has_files:
                logger.info("[TRIGGER] FileWatcher detected new files. Triggering workflow...")
                count = self.connector.sync_files()
                if count > 0:
                    logger.info(f"[TRIGGER] Auto-synced {count} files to learning memory.")
        except Exception as e:
            logger.error(f"[TRIGGER] FileWatcher error: {e}")
