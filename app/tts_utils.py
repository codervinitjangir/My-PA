"""
tts_utils.py — Shared TTS audio generation utility.

Single source of truth for audio byte generation.
Both the streaming TTS pipeline (main.py) and wake word (wake_word.py) use this.
No second audio architecture.
"""
import asyncio
import logging
import os

logger = logging.getLogger("J.A.R.V.I.S")


def generate_tts_bytes(text: str, voice: str, rate: str) -> bytes:
    """
    Generate TTS audio bytes for the given text.
    Respects VOICE_PROVIDER setting (edge-tts or ElevenLabs).
    Returns raw MP3/audio bytes — caller decides how to deliver them.
    """
    from config import (
        VOICE_PROVIDER,
        ELEVENLABS_API_KEY,
        ELEVENLABS_VOICE_ID,
        ELEVENLABS_STABILITY,
        ELEVENLABS_SIMILARITY,
        ELEVENLABS_STYLE,
        ELEVENLABS_SPEAKER_BOOST,
    )

    async def _edge_tts() -> bytes:
        import edge_tts
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        parts = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                parts.append(chunk["data"])
        return b"".join(parts)

    def _elevenlabs_tts() -> bytes:
        from elevenlabs import Voice, VoiceSettings
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        voice_obj = Voice(
            voice_id=ELEVENLABS_VOICE_ID,
            settings=VoiceSettings(
                stability=ELEVENLABS_STABILITY,
                similarity_boost=ELEVENLABS_SIMILARITY,
                style=ELEVENLABS_STYLE,
                use_speaker_boost=ELEVENLABS_SPEAKER_BOOST,
            ),
        )
        audio = client.generate(text=text, voice=voice_obj, model="eleven_multilingual_v2")
        return b"".join(list(audio))

    if VOICE_PROVIDER == "elevenlabs" and ELEVENLABS_API_KEY:
        try:
            return _elevenlabs_tts()
        except Exception as e:
            logger.warning("[TTS] ElevenLabs failed, falling back to edge-tts: %s", e)

    # Default: edge-tts (always available, no API key needed)
    return asyncio.run(_edge_tts())


def play_audio_locally(audio_bytes: bytes) -> None:
    """
    Play audio bytes on the local machine speakers.
    Used by wake word — not the browser streaming pipeline.
    Writes to a temp file, plays via Windows MCI (built-in on all modern Windows),
    then deletes the temp file.
    """
    import tempfile
    import platform

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
            f.write(audio_bytes)

        if platform.system() == "Windows":
            import ctypes
            winmm = ctypes.windll.winmm
            alias = "jarvis_local_tts"
            winmm.mciSendStringW(f'open "{tmp}" type mpegvideo alias {alias}', None, 0, None)
            winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
            winmm.mciSendStringW(f'close {alias}', None, 0, None)
        else:
            # Linux / macOS fallback — requires 'mpg123' or similar on PATH
            import subprocess
            subprocess.run(["mpg123", "-q", tmp], check=False)

    except Exception as e:
        logger.error("[TTS] Local playback failed: %s", e)
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
