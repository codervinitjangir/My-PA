# JARVIS Voice Integration (Revised Architecture)

## Overview

JARVIS has been upgraded to support premium voices using ElevenLabs, while retaining `edge-tts` as a permanent and robust fallback. This ensures JARVIS never stops speaking due to API failures, rate limits, or missing configuration.

## Features

- **ElevenLabs Integration:** Premium voices with custom tuning (Stability, Similarity, Style, Speaker Boost).
- **Graceful Fallback:** If `VOICE_PROVIDER` is set to "elevenlabs" but the API key is missing or fails, JARVIS automatically falls back to `edge-tts`.
- **Language Detection:** Uses Devanagari character detection to automatically switch `edge-tts` to the professional `hi-IN-MadhurNeural` for Hindi text, while keeping `en-GB-RyanNeural` for English and Hinglish.
- **Config-Driven:** Voice provider and settings are driven entirely by `.env` and `config.py` variables. No hardcoded logic.

## Configuration

To activate ElevenLabs, ensure your `.env` contains:
```env
VOICE_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJcg
ELEVENLABS_STABILITY=0.75
ELEVENLABS_SIMILARITY=0.85
ELEVENLABS_STYLE=0.20
ELEVENLABS_SPEAKER_BOOST=true
```

## Persona Update
The `_JARVIS_SYSTEM_PROMPT_BASE` was updated to explicitly restrict JARVIS's personality to a calm, professional, and slightly futuristic tone reminiscent of Tony Stark's assistant. JARVIS natively supports switching between Hindi, Hinglish, and English without being forced.
