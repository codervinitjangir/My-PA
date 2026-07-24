"""
app/core/config.py — Centralized Configuration Management Engine

Unified Pydantic BaseSettings loading environment variables, system paths, API credentials,
and runtime settings with strict type validation.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General System Info
    APP_NAME: str = "JARVIS AI Operating System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    PORT: int = Field(default=8000)

    # Security & Auth Credentials
    JARVIS_AUTH_TOKEN: Optional[str] = Field(default=None)
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"])

    # Groq & LLM Credentials
    GROQ_API_KEYS: List[str] = Field(default_factory=list)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    AGENT_ROUTER_SECRET: Optional[str] = Field(default=None)
    DEFAULT_LLM_MODEL: str = Field(default="llama-3.1-8b-instant")

    # Speech Engine Credentials & Settings
    DEEPGRAM_API_KEY: Optional[str] = Field(default=None)
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None)
    ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM") # Rachel default
    EDGE_TTS_VOICE: str = Field(default="en-US-ChristopherNeural")

    # System Paths
    BASE_DIR: str = BASE_DIR
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    LOGS_DIR: str = os.path.join(BASE_DIR, "app", "logs")
    MEMORY_DB_PATH: str = os.path.join(BASE_DIR, "database", "memory.db")

    def get_groq_keys(self) -> List[str]:
        """Returns non-empty list of available Groq API keys."""
        keys = [k.strip() for k in self.GROQ_API_KEYS if k and k.strip()]
        if self.GROQ_API_KEY and self.GROQ_API_KEY.strip():
            if self.GROQ_API_KEY.strip() not in keys:
                keys.insert(0, self.GROQ_API_KEY.strip())
        return keys

# Global singleton settings instance
settings = Settings()
