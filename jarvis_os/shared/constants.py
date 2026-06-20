import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
CONFIGS_DIR = os.path.join(BASE_DIR, "configs")
DATA_DIR = os.path.join(BASE_DIR, "data")

IDENTITY_FILES = {
    "profile": "boss_profile.json",
    "preferences": "boss_preferences.json",
    "devices": "boss_devices.json",
    "goals": "boss_goals.json",
    "projects": "boss_projects.json",
    "relationships": "boss_relationships.json"
}
