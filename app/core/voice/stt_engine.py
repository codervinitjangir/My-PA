"""
app/core/voice/stt_engine.py — Groq Whisper / Streaming STT Engine Implementation

Adheres to STTEngine abstract interface.
Supports rapid audio transcription with fallback through API key tiers.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from app.core.voice.interfaces import STTEngine

logger = logging.getLogger("J.A.R.V.I.S")

class GroqSTTEngine(STTEngine):
    """
    STT Engine powered by Groq Whisper.
    """
    
    def __init__(self, stt_service=None):
        self.stt_service = stt_service

    async def transcribe_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Streaming chunk transcription placeholder for real-time engines."""
        return None

    async def transcribe_final(self, full_audio_bytes: bytes) -> Dict[str, Any]:
        """Transcribe complete audio file bytes via Groq Whisper."""
        if not self.stt_service or not self.stt_service.is_available:
            return {"text": "", "error": "STT service not available."}

        # Offload blocking Groq API call to async thread pool
        result = await asyncio.to_thread(
            self.stt_service.transcribe,
            full_audio_bytes,
            "audio.wav"
        )
        return result
