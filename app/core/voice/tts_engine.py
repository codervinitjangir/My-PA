"""
app/core/voice/tts_engine.py — Sentence-Level TTS Engine Implementation

Adheres to TTSEngine abstract interface.
Synthesizes sentence strings using edge-tts or ElevenLabs streaming audio bytes in memory.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional
import edge_tts

from app.core.voice.interfaces import TTSEngine
from config import TTS_VOICE, TTS_RATE, TTS_PITCH, VOICE_PROVIDER, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

logger = logging.getLogger("J.A.R.V.I.S")

class StreamingTTSEngine(TTSEngine):
    """
    Sentence-level TTS engine streaming raw audio MP3/PCM bytes.
    """
    
    def __init__(self, voice: str = TTS_VOICE, rate: str = TTS_RATE, pitch: str = TTS_PITCH):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def synthesize_sentence(self, sentence_text: str, voice: Optional[str] = None) -> AsyncIterator[bytes]:
        """Synthesize sentence string into streaming audio MP3/PCM bytes."""
        text = sentence_text.strip()
        if not text:
            return

        target_voice = voice or self.voice

        # ElevenLabs Fallback / Provider check
        if VOICE_PROVIDER == "elevenlabs" and ELEVENLABS_API_KEY:
            try:
                from elevenlabs import Voice, VoiceSettings
                from elevenlabs.client import ElevenLabs
                client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                audio_iter = client.generate(text=text, voice=ELEVENLABS_VOICE_ID, model="eleven_multilingual_v2")
                for chunk in audio_iter:
                    if chunk:
                        yield chunk
                return
            except Exception as e:
                logger.warning("[TTS-ENGINE] ElevenLabs failed, falling back to edge-tts: %s", e)

        # Default Edge-TTS streaming
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=target_voice,
                rate=self.rate,
                pitch=self.pitch
            )
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error("[TTS-ENGINE] Edge-TTS error: %s", e)
