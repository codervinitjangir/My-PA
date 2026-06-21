import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger("J.A.R.V.I.S")

KNOWLEDGE_DROP_DIR = Path("knowledge_drop")
LEARNING_DIR = Path("learning_data")

class LocalFileConnector:
    """
    Supermemory Concept: Connectors.
    Passively scans a designated 'knowledge_drop' folder for new documents
    and automatically moves/syncs them to the 'learning_data' folder for vectorization.
    """
    def __init__(self):
        KNOWLEDGE_DROP_DIR.mkdir(exist_ok=True)
        LEARNING_DIR.mkdir(exist_ok=True)
        
    def sync_files(self) -> int:
        """Move all valid txt/md files from knowledge_drop to learning_data."""
        synced_count = 0
        try:
            for file_path in KNOWLEDGE_DROP_DIR.glob("*.*"):
                if file_path.suffix.lower() in [".txt", ".md", ".csv", ".json"]:
                    target_path = LEARNING_DIR / file_path.name
                    # Move file
                    shutil.move(str(file_path), str(target_path))
                    logger.info(f"[CONNECTOR] Synced external file to memory: {file_path.name}")
                    synced_count += 1
        except Exception as e:
            logger.error(f"[CONNECTOR] Failed to sync files: {e}")
            
        return synced_count
