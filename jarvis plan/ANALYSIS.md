# J.A.R.V.I.S — Full Project Analysis

**Analyzed by:** Antigravity AI  
**Date:** 2026-05-14  
**Author:** Vinit Jangir

---

## ✅ Plan vs Reality — What's Done?

According to the original plan, Jarvis needed 8 things. Here's what is actually built:

| # | Plan Goal | Status | Notes |
|---|-----------|--------|-------|
| 1 | Multiple Role-Specific Chatbots | ✅ DONE | `groq_service.py` (general) + `realtime_service.py` (web) + `vision_service.py` (camera) |
| 2 | Core AI Brain / Decision Model | ✅ DONE | `brain_service.py` — Two-stage LLM classify: primary category then task type |
| 3 | Text-to-Speech (TTS) | ✅ DONE | `edge-tts` with 300+ voices, streaming in `main.py`, TTS voice = en-GB-RyanNeural |
| 4 | Speech-to-Text (STT) | ❌ NOT BUILT | Only frontend mic capture exists (JS). No Whisper/Groq STT on backend |
| 5 | Intelligent Task System | ✅ DONE | `task_executor.py` + `task_manager.py` — open, play, search, generate, write |
| 6 | Vision-Based AI Layer | ✅ DONE | `vision_service.py` — Groq vision model (llama-4-scout), camera integration |
| 7 | Unified System Integration | ✅ DONE | `chat_service.py` — Brain routes to correct service in one `/chat/jarvis/stream` |
| 8 | Connected Ecosystem / Deployment | 🟡 PARTIAL | Runs on localhost:8000, no Docker/cloud deployment yet |

**Overall: ~7 out of 8 major goals are implemented. STT backend is missing.**

---

## 🐛 Bugs & Mistakes Found

### Bug 1 — CRITICAL: `_stream_generator` Indentation Error (`main.py` line 448)

```python
# WRONG (current code):
for chunk in chunk_iter:
    if isinstance(chunk, str):
        yield f"data: ..."
        buffer += chunk
        sentences, buffer = _split_sentences(buffer)
    sentences = _merge_short(sentences)   # ← THIS IS OUTSIDE the `if` block!
```

The line `sentences = _merge_short(sentences)` is **outside** the `if isinstance(chunk, str)` block due to wrong indentation. This means it runs on EVERY chunk (including dicts), causing a `NameError: name 'sentences' is not defined` when a dict chunk comes first.

**Fix:**
```python
        if isinstance(chunk, str):
            yield f"data: ..."
            buffer += chunk
            sentences, buffer = _split_sentences(buffer)
            sentences = _merge_short(sentences)  # ← Move inside the if block
```

---

### Bug 2 — `vision_service.py`: Only Uses First API Key, No Fallback

```python
# Current (uses only key index 0, always):
self._groq_client = Groq(api_key=GROQ_API_KEYS[0])
```

If the first key hits rate limit, Vision fails completely. It should rotate keys like the other services.

**Fix:**
```python
self._groq_api_keys = GROQ_API_KEYS
self._current_key_index = 0
```
And cycle through keys on failure in `_call_groq()`.

---

### Bug 3 — `key_rotation.py`: Key Rotation Is Broken (Always Returns Index 0)

```python
def get_next_key_pair(num_keys: int, need_brain: bool = True):
    if not need_brain:
        return (None, 0)   # chat always uses key 0
    if num_keys <= 1:
        return (0, 0)
    return (0, 1)           # brain uses 0, chat uses 1 — HARDCODED, no rotation!
```

This is not actual rotation. It always returns the same key indexes. If you have 3 keys, key 3 is never used.

**Fix:** Use a thread-safe counter that increments and wraps around:
```python
import threading
_counter = 0
_lock = threading.Lock()

def get_next_key_pair(num_keys: int, need_brain: bool = True):
    global _counter
    with _lock:
        idx = _counter % num_keys
        _counter += 1
    if not need_brain:
        return (None, idx)
    brain_idx = idx
    chat_idx = (idx + 1) % num_keys
    return (brain_idx, chat_idx)
```

---

### Bug 4 — `chat_service.py` line 578: Uses `user_message` Instead of `clean_user_message`

```python
# line 578 — passes RAW user_message (with cam token) instead of cleaned one:
intents = self.brain_service.extract_task_payloads(user_message, tasks, chat_history)
```

The `CAM_BYPASS_TOKEN` (`TTCAMTOKENTT`) is stripped into `clean_user_message`, but task payloads still receive the dirty original `user_message`.

**Fix:**
```python
intents = self.brain_service.extract_task_payloads(clean_user_message, tasks, chat_history)
```

---

### Bug 5 — `brain_service.py` line 346–353: Duplicate SITE_MAP Lookup

```python
def _resolve_open_query(self, query: str) -> str:
    q = query.strip().lower()
    if q in self.SITE_MAP:          # ← checks here
        return self.SITE_MAP[q]
    if "." in q:
        return f"https://{q}" if not q.startswith("http") else q
    if q in self.SITE_MAP:          # ← checks AGAIN (dead code!)
        return self.SITE_MAP[q]
    return f"https://www.{q}.com"
```

The second `if q in self.SITE_MAP` can **never** be reached because the first check already handles it. This is dead code.

**Fix:** Remove the duplicate second check.

---

### Bug 6 — `app/core/` and `app/api/` Directories Are Empty

These directories exist but are completely empty. The API routes are all jammed inside `main.py` (767 lines). This makes the code hard to maintain.

**Recommendation:** Move routes to `app/api/routes.py` and keep `main.py` as the app factory only.

---

### Bug 7 — `requirements.txt`: Missing `httpx` (Used in `task_executor.py`)

`task_executor.py` imports `httpx` for image generation:
```python
import httpx  # line 266
```

But `httpx` is **NOT listed** in `requirements.txt`. This will cause `ModuleNotFoundError` on a fresh install.

**Fix:** Add `httpx>=0.24.0` to `requirements.txt`.

---

### Bug 8 — `vision_service.py`: Camera doesn't fall back when `imgbase64` is None

In `chat_service.py`:
```python
if query_type == "vision":
     if self.vision_service and imgbase64:  # ← extra indent space = works, but...
         # ...analyze image
         return
# Falls through silently if no imgbase64 — no error message!
```

If `query_type == "vision"` but no image was attached, the code falls through silently and tries to stream a text response with the wrong context. The user gets no feedback.

**Fix:** Add an explicit else:
```python
if query_type == "vision":
    if self.vision_service and imgbase64:
        # ...analyze...
        return
    else:
        # Tell user to attach image
        no_img_msg = "Please open the webcam or attach an image so I can see what you're referring to."
        self.sessions[session_id][-1].content = no_img_msg
        yield no_img_msg
        self.save_chat_session(session_id)
        return
```

---

## 🟡 Things That Work But Can Be Improved

### Improvement 1 — STT (Speech-to-Text) is Missing Backend

The plan says "Fastest Speech Recognition Model, All Languages Supported" but backend has NO STT. The frontend might handle it via browser Web Speech API, but that's unreliable across browsers and languages.

**Recommendation:** Add Groq's Whisper endpoint (free, ultra-fast):
```python
# In a new stt_service.py:
client.audio.transcriptions.create(
    model="whisper-large-v3",
    file=audio_file,
)
```

---

### Improvement 2 — TTS Voice Is Hardcoded English Only

Config has `TTS_VOICE = "en-GB-RyanNeural"` but the plan says **All Languages Supported**. If a user speaks Hindi or Spanish, the English voice speaks back.

**Recommendation:** Auto-detect language of response and pick matching voice:
```python
VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural",
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    # etc.
}
```

---

### Improvement 3 — `groq_service.py`: `max_tokens=1024` Is Too Low for Content Tasks

When a user asks "write me an essay", the content generation goes through `task_executor.py` using the same `groq_service` which has `max_tokens=1024`. Essays can easily exceed this.

**Recommendation:** Use a separate LLM instance for content tasks with `max_tokens=4096`.

---

### Improvement 4 — No Rate Limiting on the API

Any user can hit `/chat/jarvis/stream` unlimited times. There's no per-IP or per-session rate limiting middleware.

**Recommendation:** Add `slowapi` middleware:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
@app.post("/chat/jarvis/stream")
@limiter.limit("30/minute")
async def chat_jarvis_stream(...):
```

---

### Improvement 5 — Chat History Has No Size Limit on Disk

Sessions are saved as JSON files indefinitely. With many users, the `database/chats_data/` folder will grow forever with no cleanup.

**Recommendation:** Add a cleanup job that deletes sessions older than 7 days.

---

## ✅ What's Working Well

- **Brain routing is smart** — Two-stage LLM classification with rule-based fallback is a great design.
- **Key fallback system** — Multiple Groq API keys with automatic failover is production-ready.
- **Streaming TTS** — Sentence-by-sentence parallel TTS generation is efficient.
- **Thread-safe session saving** — `_save_lock` in `chat_service.py` prevents corruption.
- **Repetition detection** — `_detect_repetition_loop` in `groq_service.py` is a clever safety net.
- **Pollinations.ai for images** — Free, no API key needed, retry logic included.
- **Vision model** — Groq's llama-4-scout for camera analysis is powerful.
- **Config is clean** — `.env` based config with sensible defaults.

---

## 📋 Priority Fix List

| Priority | Bug | File | Effort |
|----------|-----|------|--------|
| 🔴 P1 | Indentation bug in `_stream_generator` | `main.py:448` | 1 line fix |
| 🔴 P1 | `httpx` missing from requirements | `requirements.txt` | 1 line fix |
| 🔴 P1 | `clean_user_message` not passed to task payloads | `chat_service.py:578` | 1 line fix |
| 🟠 P2 | Key rotation always hardcoded to index 0/1 | `key_rotation.py` | 15 line fix |
| 🟠 P2 | Vision service no key fallback | `vision_service.py` | 20 line fix |
| 🟠 P2 | Vision: no feedback when no image attached | `chat_service.py` | 8 line fix |
| 🟡 P3 | Dead code in `_resolve_open_query` | `brain_service.py` | Remove 2 lines |
| 🟡 P3 | Add `httpx` to requirements | `requirements.txt` | 1 line |
| 🟢 P4 | Add STT backend (Groq Whisper) | New `stt_service.py` | Medium effort |
| 🟢 P4 | Multi-language TTS voice selection | `config.py` | Small effort |
