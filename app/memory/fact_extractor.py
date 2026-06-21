import logging
from app.services.vector_store import VectorStoreService
from app.memory.user_profile_manager import UserProfileManager
import time
from pathlib import Path

logger = logging.getLogger("J.A.R.V.I.S")

class FactExtractor:
    """
    Passively extracts facts from chat history and adds them to memory.
    Mem0 Concept: Single-pass ADD-only extraction. No UPDATE/DELETE.
    """
    def __init__(self, profile_manager: UserProfileManager):
        self.profile_manager = profile_manager

    def extract_and_store(self, user_message: str, assistant_response: str):
        # In a real impl, we'd use a small LLM call to extract discrete facts.
        # For this prototype, we'll extract naive keywords or just store the interaction.
        logger.info("[FACT_EXTRACTOR] Analyzing interaction for ADD-only memory...")
        
        # Example of User Profile extraction logic
        if "my name is" in user_message.lower():
            name = user_message.lower().split("my name is")[-1].strip()
            self.profile_manager.profile["name"] = name.title()
            self.profile_manager.save()
            logger.info(f"[FACT_EXTRACTOR] Updated User Profile Name: {name.title()}")
            
        if "i like" in user_message.lower() or "i prefer" in user_message.lower():
            self.profile_manager.update_preference(user_message)
            logger.info("[FACT_EXTRACTOR] Added User Preference.")
            
        # Add to vector store for semantic retrieval (Passive accumulation)
        fact = f"User: {user_message}\nAssistant: {assistant_response}"
        try:
            learning_dir = Path("learning_data")
            learning_dir.mkdir(exist_ok=True)
            with open(learning_dir / "extracted_facts.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- [TS:{int(time.time())}] ---\n{fact}\n")
        except Exception as e:
            logger.error(f"[FACT_EXTRACTOR] Failed to append fact: {e}")
