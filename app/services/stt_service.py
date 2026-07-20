"""
J.A.R.V.I.S STT (Speech-to-Text) Service
Uses Groq's Whisper API for ultra-fast, multi-language speech recognition.
Supports: wav, mp3, webm, ogg, m4a, flac, mp4
All languages supported automatically by Whisper.
"""

import io
import logging
import time
from typing import Optional

from config import GROQ_API_KEYS

logger = logging.getLogger("J.A.R.V.I.S")

# Groq Whisper model — fastest available
WHISPER_MODEL = "whisper-large-v3-turbo"

# Max audio file size (25 MB — Groq limit)
MAX_AUDIO_BYTES = 25 * 1024 * 1024

# Supported audio MIME types
SUPPORTED_MIME_TYPES = {
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/webm", "video/webm",
    "audio/ogg", "audio/opus",
    "audio/mp4", "audio/x-m4a",
    "audio/flac",
    "audio/aac",
}


class STTService:
    """
    Speech-to-Text using Groq Whisper.
    Automatically detects language and transcribes in that language.
    Falls back through all API keys on rate limit.
    """

    def __init__(self):
        self._groq_clients = []

        if not GROQ_API_KEYS:
            logger.warning("[STT] No GROQ_API_KEY found. STT will not work.")
            return

        try:
            from groq import Groq
            for key in GROQ_API_KEYS:
                self._groq_clients.append(Groq(api_key=key))
            logger.info(
                "[STT] Groq Whisper STT initialized (%s) with %d key(s)",
                WHISPER_MODEL, len(self._groq_clients)
            )
        except ImportError:
            logger.warning("[STT] 'groq' package not installed. Run: pip install groq")
        except Exception as e:
            logger.warning("[STT] Groq client init failed: %s", e)

    @property
    def is_available(self) -> bool:
        return len(self._groq_clients) > 0

    DEFAULT_PROMPT = (
        "JARVIS, Jarvis, brief, calendar, Gmail, email, CloudStream, "
        "Groq, Telegram, schedule, reminder, meeting, download, PDF, "
        "send file, screen, analyze, open, play, search"
    )

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
        # Language is explicitly left as None (auto-detect).
        # Do NOT force language='en' on Whisper, since that would cause mistranscription
        # when the user actually speaks Hindi/Hinglish. Whisper should keep auto-detecting,
        # and the LLM (not STT) handles responding in English.
        language: Optional[str] = None,
        prompt: Optional[str] = DEFAULT_PROMPT,
    ) -> dict:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Filename with extension (used to determine format)
            language: Optional ISO 639-1 language code hint (e.g. 'en', 'hi', 'es').
                      If None, Whisper auto-detects.
            prompt: Optional context/prompt to guide transcription accuracy.

        Returns:
            dict with keys:
                - text: str — transcribed text
                - language: str — detected/used language code
                - duration: float — audio duration in seconds
                - error: str | None — error message if failed
        """
        if not self._groq_clients:
            return {
                "text": "",
                "language": "unknown",
                "duration": 0.0,
                "error": "STT service not available. Check GROQ_API_KEY.",
            }

        if not audio_bytes:
            return {"text": "", "language": "unknown", "duration": 0.0, "error": "No audio data received."}

        audio_size = len(audio_bytes)

        if audio_size > MAX_AUDIO_BYTES:
            logger.warning("[STT] Audio too large: %d bytes (max %d)", audio_size, MAX_AUDIO_BYTES)
            return {
                "text": "",
                "language": "unknown",
                "duration": 0.0,
                "error": f"Audio file too large ({audio_size // 1024 // 1024}MB). Max is 25MB.",
            }

        if audio_size < 100:
            return {"text": "", "language": "unknown", "duration": 0.0, "error": "Audio too short or empty."}

        logger.info("[STT] Transcribing %d bytes, file=%s, lang=%s", audio_size, filename, language or "auto")

        # Try each API key in order until one succeeds
        last_error = None

        for attempt, client in enumerate(self._groq_clients):
            try:
                result = self._call_whisper(client, audio_bytes, filename, language, prompt, attempt)

                if result and result.get("text"):
                    return result

            except Exception as e:
                last_error = e
                err_str = str(e).lower()

                if "429" in str(e) or "rate limit" in err_str:
                    logger.warning("[STT] Key #%d rate limited, trying next...", attempt + 1)
                    continue
                else:
                    logger.warning("[STT] Key #%d failed: %s", attempt + 1, e)
                    continue

        error_msg = str(last_error) if last_error else "All API keys failed."
        logger.error("[STT] All %d keys failed. Last error: %s", len(self._groq_clients), error_msg)
        return {
            "text": "",
            "language": "unknown",
            "duration": 0.0,
            "error": "Could not transcribe audio. Please try again.",
        }

    def _call_whisper(
        self,
        client,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str],
        prompt: Optional[str],
        attempt: int,
    ) -> dict:
        t0 = time.perf_counter()

        # Build file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        # Build kwargs — only pass language if specified (auto-detect otherwise)
        kwargs = {
            "file": (filename, audio_file, self._get_mime(filename)),
            "model": WHISPER_MODEL,
            "response_format": "verbose_json",  # gives us language + duration info
            "temperature": 0.0,
        }

        if language:
            kwargs["language"] = language

        if prompt:
            kwargs["prompt"] = prompt[:500]  # Whisper prompt max ~500 chars

        response = client.audio.transcriptions.create(**kwargs)

        elapsed = time.perf_counter() - t0

        text = (getattr(response, "text", "") or "").strip()
        detected_lang = getattr(response, "language", language or "unknown")
        duration = getattr(response, "duration", 0.0) or 0.0

        logger.info(
            "[STT] Key #%d success | lang=%s | duration=%.1fs | transcription_time=%.2fs | chars=%d",
            attempt + 1, detected_lang, duration, elapsed, len(text)
        )

        return {
            "text": text,
            "language": detected_lang,
            "duration": float(duration),
            "error": None,
        }

    def _get_mime(self, filename: str) -> str:
        """Determine MIME type from file extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
        mime_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "opus": "audio/opus",
            "m4a": "audio/mp4",
            "mp4": "audio/mp4",
            "flac": "audio/flac",
            "aac": "audio/aac",
        }
        return mime_map.get(ext, "audio/webm")
