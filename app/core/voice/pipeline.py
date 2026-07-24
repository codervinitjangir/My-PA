"""
app/core/voice/pipeline.py — Unified Voice Pipeline Orchestrator

Manages bi-directional voice WebSocket interaction sessions (/voice/ws).
Supports pre-warming, adaptive VAD, fast-path intent action dispatch, sentence-level streaming TTS, and barge-in interruption.
"""

import asyncio
import json
import base64
import time
import logging
from typing import Optional, Dict, Any

from app.core.voice.interfaces import VoicePipeline
from app.core.voice.vad import AdaptiveVAD
from app.core.voice.intent_engine import FastPathIntentEngine
from app.core.voice.action_planner import DesktopActionPlanner
from app.core.voice.stt_engine import GroqSTTEngine
from app.core.voice.tts_engine import StreamingTTSEngine
from app.utils.sentence_chunker import SentenceChunker

logger = logging.getLogger("J.A.R.V.I.S")

class UnifiedVoicePipeline(VoicePipeline):
    """
    Unified voice orchestration engine for real-time JARVIS interactions.
    """
    
    def __init__(self, chat_service=None, stt_service=None, brain_service=None):
        self.chat_service = chat_service
        self.stt_engine = GroqSTTEngine(stt_service)
        self.intent_engine = FastPathIntentEngine(brain_service)
        self.action_planner = DesktopActionPlanner(confidence_threshold=0.85)
        self.tts_engine = StreamingTTSEngine()
        
        self.active_tasks = set()

    async def pre_warm_session(self, session_id: str):
        """Pre-warm LLM connections and pre-fetch context on wake word trigger."""
        t0 = time.perf_counter()
        logger.info("[PIPELINE] Pre-warming session %s...", session_id[:12])
        try:
            # Touch session in chat service (warm LRU cache)
            if self.chat_service:
                self.chat_service.get_or_create_session(session_id)
        except Exception as e:
            logger.warning("[PIPELINE] Pre-warm warning: %s", e)
        logger.info("[PIPELINE] Session pre-warmed in %.1fms", (time.perf_counter() - t0) * 1000)

    async def process_voice_session(self, websocket: Any) -> None:
        """Process incoming WebSocket binary and control frames."""
        session_id = f"voice-{int(time.time())}"
        vad = AdaptiveVAD(silence_duration_ms=300)
        audio_buffer = bytearray()
        
        current_llm_task: Optional[asyncio.Task] = None
        current_tts_task: Optional[asyncio.Task] = None

        logger.info("[VOICE-WS] Session started: %s", session_id)

        try:
            while True:
                message = await websocket.receive()
                
                # Check frame type
                if "bytes" in message and message["bytes"]:
                    data = message["bytes"]
                    header = data[0:1]
                    payload = data[1:]
                    
                    if header == b'\x01':  # PCM audio chunk frame
                        audio_buffer.extend(payload)
                        pcm_chunk = np.frombuffer(payload, dtype=np.int16)
                        vad_res = vad.process_frame(pcm_chunk)
                        
                        if vad_res["speech_ended"]:
                            logger.info("[VOICE-WS] Adaptive VAD speech ended! Audio size: %d bytes", len(audio_buffer))
                            # Cancel any previous speech task (barge-in / new speech)
                            if current_llm_task and not current_llm_task.done():
                                current_llm_task.cancel()
                            if current_tts_task and not current_tts_task.done():
                                current_tts_task.cancel()

                            captured_audio = bytes(audio_buffer)
                            audio_buffer.clear()
                            vad.reset()

                            # Dispatch speech processing pipeline task
                            current_llm_task = asyncio.create_task(
                                self._run_voice_turn(websocket, session_id, captured_audio)
                            )
                    continue

                elif "text" in message and message["text"]:
                    try:
                        event_data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue
                        
                    event_type = event_data.get("event")
                    
                    if event_type == "wake_detected":
                        await self.pre_warm_session(session_id)
                        audio_buffer.clear()
                        vad.reset()
                        await websocket.send_json({"event": "ready", "status": "listening"})

                    elif event_type == "barge_in":
                        logger.info("[VOICE-WS] Barge-in event received! Halting ongoing TTS & LLM tasks.")
                        if current_llm_task and not current_llm_task.done():
                            current_llm_task.cancel()
                        if current_tts_task and not current_tts_task.done():
                            current_tts_task.cancel()
                        audio_buffer.clear()
                        vad.reset()
                        await websocket.send_json({"event": "audio_stop"})

        except Exception as e:
            logger.info("[VOICE-WS] Session ended for %s: %s", session_id, e)
        finally:
            if current_llm_task and not current_llm_task.done():
                current_llm_task.cancel()

    async def _run_voice_turn(self, websocket: Any, session_id: str, audio_bytes: bytes):
        """Run single voice turn pipeline (STT -> Intent -> Action / LLM -> Sentence TTS)."""
        t_start = time.perf_counter()
        
        # 1. STT Transcription
        stt_res = await self.stt_engine.transcribe_final(audio_bytes)
        text = (stt_res.get("text") or "").strip()
        
        if not text:
            logger.info("[VOICE-WS] STT produced no text.")
            await websocket.send_json({"event": "stt_empty"})
            return

        stt_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info("[VOICE-WS] STT Transcript in %dms: '%s'", stt_ms, text)
        await websocket.send_json({"event": "stt_result", "text": text, "stt_ms": stt_ms})

        # 2. Fast-Path Intent Classification
        intent = await self.intent_engine.classify_intent(text)
        logger.info("[VOICE-WS] Intent classified: type=%s action=%s confidence=%.2f",
                    intent.intent_type, intent.action, intent.confidence)

        # 3. High-Confidence Action Execution (~100ms post-STT)
        if intent.confidence >= 0.85 and intent.intent_type == "action":
            action_res = await self.action_planner.execute_action(intent)
            action_ms = int((time.perf_counter() - t_start) * 1000)
            logger.info("[VOICE-WS] Desktop action executed in %dms!", action_ms)
            await websocket.send_json({"event": "action_executed", "action": intent.action, "elapsed_ms": action_ms})
            
            # Synthesize short voice confirmation
            speak_msg = f"Opening {intent.target}." if intent.action == "open_app" else "Done, sir."
            async for chunk in self.tts_engine.synthesize_sentence(speak_msg):
                b64_audio = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({"event": "audio_chunk", "data": b64_audio})
            return

        # 4. LLM Generation + Sentence-Level TTS Streaming
        if not self.chat_service:
            return

        sentence_chunker = SentenceChunker()
        t_llm_start = time.perf_counter()
        first_audio_sent = False

        try:
            # Parallel Context Retrieval Timeout Budget (50ms)
            ctx_task = asyncio.create_task(asyncio.sleep(0.01))  # Lightweight context placeholder
            await asyncio.wait_for(ctx_task, timeout=0.05)
        except asyncio.TimeoutError:
            pass

        # Stream tokens from ChatService
        try:
            token_iter = self.chat_service.process_message_stream(session_id, text)
            for token in token_iter:
                if isinstance(token, dict):
                    continue
                    
                sentences = sentence_chunker.process_token(token)
                for sentence in sentences:
                    # Synthesize sentence #1 immediately
                    async for audio_chunk in self.tts_engine.synthesize_sentence(sentence):
                        if not first_audio_sent:
                            ttfa_ms = int((time.perf_counter() - t_start) * 1000)
                            logger.info("[VOICE-WS] TIME-TO-FIRST-AUDIO (TTFA): %dms!", ttfa_ms)
                            first_audio_sent = True
                            
                        b64_audio = base64.b64encode(audio_chunk).decode("utf-8")
                        await websocket.send_json({"event": "audio_chunk", "data": b64_audio, "text": sentence})

            # Flush remaining sentence
            for final_sentence in sentence_chunker.flush():
                async for audio_chunk in self.tts_engine.synthesize_sentence(final_sentence):
                    b64_audio = base64.b64encode(audio_chunk).decode("utf-8")
                    await websocket.send_json({"event": "audio_chunk", "data": b64_audio, "text": final_sentence})

            await websocket.send_json({"event": "turn_complete"})

        except asyncio.CancelledError:
            logger.info("[VOICE-WS] Turn cancelled by barge-in or new input.")
        except Exception as e:
            logger.error("[VOICE-WS] Pipeline error: %s", e)

import numpy as np
