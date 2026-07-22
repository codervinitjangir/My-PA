"""
jarvis_desktop/laptop_client.py

Lightweight WebSocket Companion Client.
Connects your local laptop to the JARVIS backend running on Render (cloud).

Handles two server commands:
  - open_app       : Opens a local application / URL using os.startfile
  - capture_screen : Takes a screenshot and returns it as base64 to the server

With Always-On Wake Word functionality built-in.
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
import subprocess
import threading
import queue
import tempfile
import time
import wave
import uuid
import httpx
import numpy as np

try:
    import websockets
except ImportError:
    print("[ERROR] websockets library not found. Run: pip install websockets")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")
API_TOKEN  = os.getenv("JARVIS_API_TOKEN", "")
API_KEY    = os.getenv("JARVIS_API_KEY", "")
WAKE_WORD_ENABLED = os.getenv("JARVIS_WAKE_WORD_ENABLED", "true").lower() == "true"

if not RENDER_URL:
    print("[ERROR] RENDER_URL is not set in your .env file.")
    print("  Add: RENDER_URL=https://your-app.onrender.com")
    sys.exit(1)

# Build WebSocket URL
WS_URL = RENDER_URL.replace("https://", "wss://").replace("http://", "ws://") + "/laptop/ws"
if API_TOKEN:
    WS_URL += f"?token={API_TOKEN}"

# Build Auth Headers for HTTP Requests
# Send BOTH tokens: AuthMiddleware checks Bearer, /chat checks X-API-Key.
# Use API_KEY as Bearer fallback if API_TOKEN doesn't match the server's value.
_bearer = API_TOKEN or API_KEY
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if _bearer:
    HEADERS["Authorization"] = f"Bearer {_bearer}"
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

RECONNECT_DELAY_INITIAL = 5
RECONNECT_DELAY_MAX     = 60

# Backend chat API requires a strict UUID4 session ID
CLIENT_SESSION_ID = str(uuid.uuid4())

# Persistent HTTP client — reuses TCP connections across all STT/chat/TTS calls
# This avoids a fresh TCP+TLS handshake on every voice interaction
HTTP_CLIENT = httpx.Client(
    base_url=RENDER_URL,
    headers=HEADERS,
    timeout=httpx.Timeout(connect=10.0, read=45.0, write=45.0, pool=10.0),
    follow_redirects=True,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("laptop_client.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("JARVIS.LaptopClient")


# ── Handlers ──────────────────────────────────────────────────────────────────

def handle_open_app(payload: dict) -> dict:
    target = (payload.get("target") or "").strip()
    if not target:
        return {"status": "error", "message": "No target specified"}

    if target.lower() in ("lock_screen", "lock_pc", "lock", "system:lock_screen"):
        return handle_lock_screen(payload)

    if "scroll" in target.lower():
        direction = "up" if "up" in target.lower() else "down"
        return handle_scroll({"direction": direction, "amount": 500})

    if target.lower() in ("telegram", "telegram.exe"):
        appdata = os.getenv("APPDATA", "")
        tg_path = os.path.join(appdata, "Telegram Desktop", "Telegram.exe")
        if os.path.exists(tg_path):
            target = tg_path
        else:
            try:
                import webbrowser
                webbrowser.open("https://web.telegram.org")
                return {"status": "success", "message": "Opened Telegram Web"}
            except Exception as e:
                logger.error("[OPEN] Failed to open Telegram Web: %s", e)
                return {"status": "error", "message": str(e)}
    try:
        os.startfile(target)
        logger.info("[OPEN] Opened: %s", target)
        return {"status": "success", "message": f"Opened {target}"}
    except Exception as e:
        try:
            subprocess.Popen(["start", "", target], shell=True)
            logger.info("[OPEN] Opened via shell: %s", target)
            return {"status": "success", "message": f"Opened {target}"}
        except Exception as e2:
            logger.error("[OPEN] Failed to open %s: %s", target, e2)
            return {"status": "error", "message": str(e2)}

def handle_capture_screen(payload: dict) -> dict:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        raw_bytes = buf.getvalue()
        buf.close()
        img.close()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info("[SCREEN] Screenshot captured (%d bytes)", len(raw_bytes))
        return {"status": "success", "image_b64": b64}
    except ImportError:
        return {"status": "error", "message": "Pillow not installed."}
    except Exception as e:
        logger.error("[SCREEN] Capture failed: %s", e)
        return {"status": "error", "message": str(e)}

def handle_volume_set(payload: dict) -> dict:
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        import ctypes
        
        action = payload.get("action", "volume_set")
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        
        if action == "volume_mute":
            volume.SetMute(1, None)
            logger.info("[ACTION] Volume muted")
            return {"success": True, "message": "Volume muted"}
        elif action == "volume_unmute":
            volume.SetMute(0, None)
            logger.info("[ACTION] Volume unmuted")
            return {"success": True, "message": "Volume unmuted"}
        else:
            level = payload.get("level")
            if level is None:
                return {"success": False, "error": "No volume level provided"}
            level = max(0, min(100, int(level)))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            logger.info("[ACTION] Volume set to %s%%", level)
            return {"success": True, "message": f"Volume set to {level}%"}
    except Exception as e:
        logger.error("[ACTION] Volume control failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_brightness_set(payload: dict) -> dict:
    try:
        import screen_brightness_control as sbc
        level = payload.get("level")
        if level is None:
            return {"success": False, "error": "No brightness level provided"}
        level = max(0, min(100, int(level)))
        sbc.set_brightness(level)
        logger.info("[ACTION] Brightness set to %s%%", level)
        return {"success": True, "message": f"Brightness set to {level}%"}
    except Exception as e:
        logger.error("[ACTION] Brightness control failed: %s", e)
        return {"success": False, "error": f"Brightness control failed: {str(e)}"}

def handle_lock_screen(payload: dict) -> dict:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        logger.info("[ACTION] Screen locked")
        return {"success": True, "message": "Screen locked"}
    except Exception as e:
        logger.error("[ACTION] Screen lock failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_clipboard_get(payload: dict) -> dict:
    try:
        import pyperclip
        action = payload.get("action", "clipboard_get")
        if action == "clipboard_set":
            text = payload.get("text", "")
            pyperclip.copy(text)
            logger.info("[ACTION] Clipboard set")
            return {"success": True, "message": "Clipboard set"}
        else:
            text = pyperclip.paste()
            logger.info("[ACTION] Clipboard read")
            return {"success": True, "text": text}
    except Exception as e:
        logger.error("[ACTION] Clipboard operation failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_wifi_toggle(payload: dict) -> dict:
    try:
        import subprocess
        state = str(payload.get("state", "")).lower()
        if state not in ["on", "off"]:
            return {"success": False, "error": "State must be 'on' or 'off'"}
        
        cmd_state = "enabled" if state == "on" else "disabled"
        result = subprocess.run(
            ['netsh', 'interface', 'set', 'interface', 'Wi-Fi', cmd_state],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            err = result.stderr.strip() if result.stderr else (result.stdout.strip() if result.stdout else "Permission denied or interface not found")
            logger.error("[ACTION] WiFi toggle failed: %s", err)
            return {"success": False, "error": err}
            
        logger.info("[ACTION] WiFi turned %s", state)
        return {"success": True, "message": f"WiFi turned {state}"}
    except Exception as e:
        logger.error("[ACTION] WiFi toggle failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_keyboard_shortcut(payload: dict) -> dict:
    try:
        import keyboard
        shortcut = payload.get("shortcut", "")
        if shortcut:
            keyboard.send(shortcut)
            logger.info("[ACTION] Keyboard shortcut sent: %s", shortcut)
            return {"success": True, "message": f"Sent shortcut {shortcut}"}
        return {"success": False, "error": "No shortcut provided"}
    except Exception as e:
        logger.error("[ACTION] Keyboard shortcut failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_type_text(payload: dict) -> dict:
    try:
        import keyboard
        text = payload.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
            
        if len(text) > 500:
            logger.warning("[ACTION] Refused to type text longer than 500 characters (%d chars)", len(text))
            return {"success": False, "error": "Text too long (max 500 chars)"}
            
        keyboard.write(text)
        logger.info("[ACTION] Typed text: %s", text)
        return {"success": True, "message": "Text typed successfully"}
    except Exception as e:
        logger.error("[ACTION] Type text failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_scroll(payload: dict) -> dict:
    try:
        import pyautogui
        direction = payload.get("direction", "down")
        amount = int(payload.get("amount", 3))
        scroll_val = amount if direction == "up" else -amount
        pyautogui.scroll(scroll_val)
        logger.info("[ACTION] Scrolled %s by %s", direction, amount)
        return {"success": True, "message": f"Scrolled {direction}"}
    except Exception as e:
        logger.error("[ACTION] Scroll failed: %s", e)
        return {"success": False, "error": str(e)}

def handle_open_url(payload: dict) -> dict:
    url = (payload.get("url") or payload.get("target") or "").strip()
    if not url:
        return {"status": "error", "message": "No url specified"}
    try:
        import webbrowser
        webbrowser.open(url)
        logger.info("[URL] Opened: %s", url)
        return {"status": "success", "message": f"Opened {url}"}
    except Exception as e:
        logger.error("[URL] Failed to open %s: %s", url, e)
        return {"status": "error", "message": str(e)}

HANDLERS = {
    "open_url":          handle_open_url,
    "open_app":          handle_open_app,
    "capture_screen":    handle_capture_screen,
    "volume_set":        handle_volume_set,
    "volume_mute":       lambda p: handle_volume_set({"action": "volume_mute", **p}),
    "volume_unmute":     lambda p: handle_volume_set({"action": "volume_unmute", **p}),
    "brightness_set":    handle_brightness_set,
    "lock_screen":       handle_lock_screen,
    "clipboard_get":     handle_clipboard_get,
    "clipboard_set":     lambda p: handle_clipboard_get({"action": "clipboard_set", **p}),
    "wifi_toggle":       handle_wifi_toggle,
    "keyboard_shortcut": handle_keyboard_shortcut,
    "type_text":         handle_type_text,
    "scroll":            handle_scroll,
}

async def _process(websocket, message: str):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
    action  = data.get("action", "")
    msg_id  = data.get("msg_id", "")
    payload = data.get("payload", {})
    handler = HANDLERS.get(action)
    if handler:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, handler, payload)
    else:
        result = {"status": "error", "message": f"Unknown action: {action}"}
    result["msg_id"] = msg_id
    await websocket.send(json.dumps(result))

async def connect_and_listen():
    delay = RECONNECT_DELAY_INITIAL
    while True:
        try:
            logger.info("[WS] Connecting to %s ...", WS_URL)
            async with websockets.connect(
                WS_URL, 
                ping_interval=20, 
                ping_timeout=30,
                user_agent_header=HEADERS["User-Agent"]
            ) as ws:
                logger.info("[WS] Connected to JARVIS server!")
                delay = RECONNECT_DELAY_INITIAL
                async for message in ws:
                    asyncio.ensure_future(_process(ws, message))
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("[WS] Closed with error: %s", e)
        except OSError as e:
            logger.warning("[WS] Network error: %s", e)
        except Exception as e:
            logger.error("[WS] Unexpected error: %s", e)
        await asyncio.sleep(delay)
        delay = min(delay * 2, RECONNECT_DELAY_MAX)

# ── Wake Word Daemon ──────────────────────────────────────────────────────────

WAKE_WORD_PAUSED = False
_LAST_WAKE_TIME = 0.0  # epoch seconds of last trigger
_WAKE_COOLDOWN_SECS = 2.0  # min seconds between triggers
QUIT_FLAG = False
TRAY_ICON = None

def generate_tray_icon(listening=True):
    try:
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        d = ImageDraw.Draw(image)
        color = (0, 255, 0) if listening else (255, 0, 0)
        d.ellipse((16, 16, 48, 48), fill=color)
        return image
    except ImportError:
        return None

def on_pause_resume(icon, item):
    global WAKE_WORD_PAUSED, TRAY_ICON
    WAKE_WORD_PAUSED = not WAKE_WORD_PAUSED
    if TRAY_ICON:
        TRAY_ICON.icon = generate_tray_icon(not WAKE_WORD_PAUSED)
        TRAY_ICON.title = "JARVIS: Listening" if not WAKE_WORD_PAUSED else "JARVIS: Paused"

def on_quit(icon, item):
    global QUIT_FLAG, TRAY_ICON
    QUIT_FLAG = True
    if TRAY_ICON:
        TRAY_ICON.stop()
    os._exit(0)

def run_tray_icon():
    global TRAY_ICON
    try:
        from pystray import Icon, Menu, MenuItem
        img = generate_tray_icon(not WAKE_WORD_PAUSED)
        if not img:
            return
        TRAY_ICON = Icon("JARVIS", img, "JARVIS: Listening")
        TRAY_ICON.menu = Menu(
            MenuItem(lambda text: "Resume" if WAKE_WORD_PAUSED else "Pause", on_pause_resume),
            MenuItem("Quit", on_quit)
        )
        TRAY_ICON.run()
    except Exception as e:
        logger.error("[TRAY] Failed to start system tray icon: %s", e)

def beep():
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass

def wake_word_thread():
    global WAKE_WORD_PAUSED, QUIT_FLAG
    try:
        import sounddevice as sd
        from openwakeword.model import Model
    except ImportError as e:
        logger.error("[WAKE] Missing dependency: %s", e)
        return

    logger.info("[WAKE] Loading openwakeword model 'hey_jarvis'...")
    try:
        owwModel = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    except Exception as e:
        logger.error("[WAKE] Failed to load openwakeword: %s", e)
        return
        
    logger.info("[WAKE] Model loaded. Monitoring microphone...")

    FORMAT = np.int16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio_queue = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            pass # ignore warnings
        audio_queue.put(indata.copy())

    # Wait a moment for UI/models
    time.sleep(1)

    while not QUIT_FLAG:
        if WAKE_WORD_PAUSED:
            time.sleep(0.5)
            continue
            
        try:
            # We explicitly open the stream. If Paused, we exit this inner loop and close the stream.
            with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK, callback=callback):
                logger.info("[WAKE] Input stream started.")
                
                # clear queue
                while not audio_queue.empty():
                    audio_queue.get()

                while not QUIT_FLAG and not WAKE_WORD_PAUSED:
                    try:
                        audio_chunk = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                        
                    pcm = audio_chunk.flatten()
                    prediction = owwModel.predict(pcm)
                    
                    for mdl, score in prediction.items():
                        if score > 0.2:
                            logger.info("[WAKE] Partial match score: %.2f", score)
                            
                        if score >= 0.42:
                            now = time.time()
                            global _LAST_WAKE_TIME
                            if now - _LAST_WAKE_TIME < _WAKE_COOLDOWN_SECS:
                                logger.info("[WAKE] Trigger suppressed (cooldown %.1fs remaining)",
                                            _WAKE_COOLDOWN_SECS - (now - _LAST_WAKE_TIME))
                                continue
                            _LAST_WAKE_TIME = now
                            logger.info("[WAKE] Wake word detected! (Score: %.2f)", score)
                            handle_wake_detection()
                            
                            # Flush queue so we don't immediately double trigger
                            while not audio_queue.empty():
                                audio_queue.get()
                            break
                            
            logger.info("[WAKE] Input stream stopped (Paused).")
            
        except Exception as e:
            logger.error("[WAKE] InputStream error: %s", e)
            time.sleep(2)

def handle_wake_detection():
    beep()
    
    import sounddevice as sd
    RATE = 16000
    CHANNELS = 1
    FORMAT = np.int16
    MAX_SECS = 5
    SILENCE_SECS = 1.5
    SILENCE_THRESHOLD = 500

    frames = []
    silent_chunks = 0
    chunks_per_sec = RATE / 1024
    max_silent_chunks = int(SILENCE_SECS * chunks_per_sec)

    logger.info("[WAKE] Recording...")
    
    with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=1024) as stream:
        silence_start_time = None
        for _ in range(int(MAX_SECS * chunks_per_sec)):
            data, overflow = stream.read(1024)
            frames.append(data)
            rms = np.sqrt(np.mean(data.astype(np.float32)**2))
            
            if rms < SILENCE_THRESHOLD:
                if silent_chunks == 0:
                    silence_start_time = time.perf_counter()
                silent_chunks += 1
            else:
                silent_chunks = 0
                silence_start_time = None
                
            if silent_chunks > max_silent_chunks:
                logger.info("[WAKE] Silence detected, stopping.")
                break

    vad_time = int((time.perf_counter() - silence_start_time) * 1000) if silence_start_time else 0
    metrics = {"VAD": vad_time, "silence_start_time": silence_start_time or time.perf_counter()}

    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    wav_bytes = wav_io.getvalue()
    wav_io.close()

    # STT Request
    try:
        audio_size_bytes = len(wav_bytes)
        audio_duration_secs = audio_size_bytes / (16000 * 2)  # 16kHz, 16-bit (2 bytes/sample)
        logger.info("[AUDIO] Uploading WAV: size=%d bytes (~%.1fs of audio, uncompressed PCM)",
                    audio_size_bytes, audio_duration_secs)
        files = {'file': ('audio.wav', wav_bytes, 'audio/wav')}
        stt_rtt_start = time.perf_counter()
        r = HTTP_CLIENT.post("/stt", files=files)
        stt_rtt_end = time.perf_counter()
        stt_rtt_ms = int((stt_rtt_end - stt_rtt_start) * 1000)
        metrics["STT"] = stt_rtt_ms
        metrics["_stt_rtt"] = stt_rtt_ms
        r.raise_for_status()
        stt_resp = r.json()
        stt_server_ms = stt_resp.get("transcription_time_ms")
        if stt_server_ms:
            logger.info("[NETWORK] STT: rtt=%dms | server_processing=%dms | network_overhead=%dms",
                        stt_rtt_ms, stt_server_ms, stt_rtt_ms - stt_server_ms)
        else:
            logger.info("[NETWORK] STT: rtt=%dms", stt_rtt_ms)
        text = stt_resp.get("text", "").strip()
        if not text:
            logger.info("[WAKE] No speech detected.")
            return
        logger.info("[WAKE] Recognized (raw): %s", text)

        # Strip wake word prefix so "Hey Jarvis, open YouTube" → "open YouTube"
        import re as _re
        text = _re.sub(
            r'^\s*(hey|hello|hi|ok|yo)?\s*jarvis[,;:!.\s]*',
            '', text, count=1, flags=_re.IGNORECASE
        ).strip()
        if not text:
            text = "Hello"  # They just said the wake word with no command
        logger.info("[WAKE] Command after stripping wake word: %s", text)
    except Exception as e:
        logger.error("[WAKE] STT failed: %s", e)
        return
        
    # Chat Request
    try:
        chat_payload = {"message": text, "session_id": CLIENT_SESSION_ID}
        chat_rtt_start = time.perf_counter()
        r2 = HTTP_CLIENT.post("/chat", json=chat_payload)
        chat_rtt_end = time.perf_counter()
        chat_rtt_ms = int((chat_rtt_end - chat_rtt_start) * 1000)
        metrics["_chat_rtt"] = chat_rtt_ms
        r2.raise_for_status()
        chat_resp = r2.json()
        
        metrics["Memory"] = chat_resp.get("memory_ms") or 0
        metrics["LLM_first"] = chat_resp.get("llm_first_ms") or 0
        metrics["LLM_total"] = chat_resp.get("llm_total_ms") or 0
        
        llm_total = metrics["LLM_total"]
        chat_overhead_ms = max(0, chat_rtt_ms - llm_total) if llm_total else chat_rtt_ms
        logger.info("[NETWORK] Chat: rtt=%dms | server_llm=%dms | network+overhead=%dms",
                    chat_rtt_ms, llm_total, chat_overhead_ms)
        
        reply_text = chat_resp.get("response", "").strip()
        logger.info("[WAKE] JARVIS replied: %s", reply_text)
        
        # --- Auto-Open URLs & Apps ---
        import re
        urls = re.findall(r'(https?://[^\s)\]]+)', reply_text)
        if urls:
            try:
                os.startfile(urls[0])
                logger.info("[WAKE] Auto-opened URL from reply: %s", urls[0])
            except Exception as e:
                logger.error("[WAKE] Failed to auto-open URL: %s", e)

        # Also detect app launch commands in reply text (e.g. "Notepad is now open")
        app_matches = re.findall(r'(?:launch(?:ed)?|open(?:ed)?|start(?:ed)?)\s+(notepad|calculator|calc|cmd|powershell|explorer|chrome|code|vscode)', reply_text, re.IGNORECASE)
        if app_matches and not urls:
            app_target = app_matches[0].lower()
            logger.info("[WAKE] Auto-opening app from reply: %s", app_target)
            handle_open_app({"target": app_target})

        # Detect lock screen or scroll in voice mode reply text
        if any(w in reply_text.lower() for w in ["locked your pc", "locked your screen", "lock signal", "screen locked"]):
            logger.info("[WAKE] Auto-locking screen from reply text")
            handle_lock_screen({})

        if "scrolled" in reply_text.lower():
            direction = "up" if "up" in reply_text.lower() else "down"
            logger.info("[WAKE] Auto-scrolling %s from reply text", direction)
            handle_scroll({"direction": direction, "amount": 500})
        
        if reply_text:
            # Strip the URL so Jarvis doesn't awkwardly read out "h t t p s colon slash slash..."
            speak_text = re.sub(r'https?://[^\s)\]]+', '', reply_text).strip()
            if not speak_text and urls:
                speak_text = "Opening that for you, sir."
            if speak_text:
                play_tts(speak_text, metrics)
            
    except Exception as e:
        logger.error("[WAKE] Chat failed: %s", e)

def play_tts(text, metrics=None):
    try:
        import pygame
        
        tts_rtt_start = time.perf_counter()
        with HTTP_CLIENT.stream("POST", "/tts", json={"text": text}) as r:
            r.raise_for_status()
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            first_chunk = True
            tts_rtt_end = None
            with os.fdopen(fd, 'wb') as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    if chunk:
                        if first_chunk and metrics is not None:
                            tts_first_time = time.perf_counter()
                            tts_rtt_end = tts_first_time
                            metrics["TTS_first"] = int((tts_first_time - tts_rtt_start) * 1000)
                            metrics["_tts_rtt_first"] = metrics["TTS_first"]
                            
                            total_time = int((tts_first_time - metrics["silence_start_time"]) * 1000)
                            metrics["Total"] = total_time
                            
                            gap_ms = total_time - (
                                metrics.get("VAD", 0) +
                                metrics.get("_stt_rtt", 0) +
                                metrics.get("_chat_rtt", 0) +
                                metrics.get("TTS_first", 0)
                            )
                            
                            logger.info("[LATENCY] VAD=%sms STT=%sms Memory=%sms LLM_first=%sms LLM_total=%sms TTS_first=%sms Total=%sms",
                                metrics.get('VAD'), metrics.get('STT'), metrics.get('Memory'), 
                                metrics.get('LLM_first'), metrics.get('LLM_total'), 
                                metrics.get('TTS_first'), metrics.get('Total')
                            )
                            logger.info("[NETWORK] stt_roundtrip=%dms chat_roundtrip=%dms tts_first_byte=%dms | unaccounted_gap=%dms",
                                metrics.get('_stt_rtt', 0),
                                metrics.get('_chat_rtt', 0),
                                metrics.get('TTS_first', 0),
                                gap_ms
                            )
                            first_chunk = False
                        f.write(chunk)

        logger.info("[WAKE] Playing TTS response...")
        global WAKE_WORD_PAUSED
        WAKE_WORD_PAUSED = True
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.quit()
        finally:
            time.sleep(0.6)  # Give speaker echo time to clear
            WAKE_WORD_PAUSED = False

        
        try:
            os.remove(temp_path)
        except Exception:
            pass
        
    except Exception as e:
        logger.error("[WAKE] TTS play failed: %s", e)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  J.A.R.V.I.S  Laptop Companion Client")
    print("=" * 55)
    print(f"  Server    : {RENDER_URL}")
    print(f"  Token     : {'set' if API_TOKEN else 'not set'}")
    print(f"  API Key   : {'set' if API_KEY else 'not set'}")
    print(f"  Wake Word : {'Enabled' if WAKE_WORD_ENABLED else 'Disabled'}")
    print("=" * 55)
    print("  Press Ctrl+C to stop.\n")

    if WAKE_WORD_ENABLED:
        threading.Thread(target=wake_word_thread, daemon=True).start()
        threading.Thread(target=run_tray_icon, daemon=True).start()

    try:
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\n[INFO] Laptop client stopped.")
        global QUIT_FLAG
        QUIT_FLAG = True
        os._exit(0)

if __name__ == "__main__":
    main()

