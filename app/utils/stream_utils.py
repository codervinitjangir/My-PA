import re
import json
import time
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from config import TTS_RATE

logger = logging.getLogger("J.A.R.V.I.S")

_SPLIT_RE = re.compile(r"(?<=[:.!?;\n])\s+")
_MIN_WORDS_FIRST = 1
_MIN_WORDS = 1
_MERGE_IF_WORDS = 2
_TTS_BUFFER_TIMEOUT = 2.0
_TTS_BUFFER_MIN_WORDS = 4
_ABBREV_HOLD_RE = re.compile(r"^(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|Vs|Etc)\.$", re.IGNORECASE)

def _should_hold_sentence_for_continuation(sent: str) -> bool:
    t = sent.strip()
    if not t.endswith("."):
        return False
    words = t.split()
    if len(words) != 1:
        return False
    return bool(_ABBREV_HOLD_RE.match(words[0]))

def _split_sentences(buf: str):
    parts = _SPLIT_RE.split(buf)
    if len(parts) <= 1:
        return [], buf
    raw = [p.strip() for p in parts[:-1] if p.strip()]
    sentences, pending = [], ""
    for s in raw:
        if pending:
            s = (pending + " " + s).strip()
            pending = ""
        min_req = _MIN_WORDS_FIRST if not sentences else _MIN_WORDS
        if len(s.split()) < min_req:
            pending = s
            continue
        sentences.append(s)
    remaining = (pending + " " + parts[-1].strip()).strip() if pending else parts[-1].strip()
    return sentences, remaining

def _merge_short(sentences):
    if not sentences:
        return []
    merged, i = [], 0
    while i < len(sentences):
        cur = sentences[i]
        j = i + 1
        while j < len(sentences) and len(sentences[j].split()) <= _MERGE_IF_WORDS:
            cur = (cur + " " + sentences[j]).strip()
            j += 1
        merged.append(cur)
        i = j
    return merged

def _generate_tts_sync(text: str, voice: str, rate: str) -> bytes:
    """Delegates to the shared TTS utility — single source of truth for audio generation."""
    from app.tts_utils import generate_tts_bytes
    return generate_tts_bytes(text, voice, rate)

def is_hindi_text(text: str) -> bool:
    """Check if the text contains Devanagari (Hindi) characters or common Hinglish words."""
    # Check for Devanagari script first
    for char in text:
        if '\u0900' <= char <= '\u097F':
            return True
            
    # Check for common Hinglish keywords (case-insensitive, whole words)
    import re
    hinglish_keywords = {
        r'\bhai\b', r'\bkaise\b', r'\bho\b', r'\bmera\b', r'\bmujhe\b', 
        r'\bkya\b', r'\btoh\b', r'\bkuch\b', r'\bnahi\b', r'\byaar\b',
        r'\baccha\b', r'\bthik\b', r'\bhaan\b', r'\bkyu\b', r'\bmatlab\b'
    }
    
    text_lower = text.lower()
    for keyword in hinglish_keywords:
        if re.search(keyword, text_lower):
            return True
            
    return False

_tts_pool = ThreadPoolExecutor(max_workers=4)

def _stream_generator(session_id: str, chunk_iter, is_realtime: bool, tts_enabled: bool = False):
    yield f"data: {json.dumps({'session_id': session_id, 'chunk': '', 'done': False})}\n\n"
    buffer = ""

    held = None
    is_first = True
    audio_queue = []
    last_submit_time = time.perf_counter()

    def _submit(text):
        nonlocal last_submit_time
        from config import TTS_VOICE, TTS_RATE
        if not text or not text.strip():
            return
        voice = "hi-IN-MadhurNeural" if is_hindi_text(text) else TTS_VOICE
        audio_queue.append((_tts_pool.submit(_generate_tts_sync, text, voice, TTS_RATE), text))
        last_submit_time = time.perf_counter()

    def _drain_ready():
        events = []
        while audio_queue and audio_queue[0][0].done():
            fut, sent = audio_queue.pop(0)
            try:
                audio = fut.result()
                b64 = base64.b64encode(audio).decode("ascii")
                events.append(f"data: {json.dumps({'audio': b64, 'sentence': sent})}\n\n")
            except Exception as exc:
                logger.warning("[TTS-INLINE] Failed for '%s': %s", sent[:40], exc)
        return events

    def _yield_completed_audio():
        if not tts_enabled:
            return
        for ev in _drain_ready():
            yield ev

    try:
        for chunk in chunk_iter:
            if isinstance(chunk, dict):
                payload = chunk
                if "activity" in chunk and "_activity" not in chunk:
                    payload = {"activity": chunk["activity"]}
                elif "_activity" in chunk:
                    payload = {"activity": chunk["_activity"]}
                if "search_results" in chunk and "_search_results" not in chunk:
                    payload = {"search_results": chunk["search_results"]}
                elif "_search_results" in chunk:
                    payload = {"search_results": chunk["_search_results"]}
                if "background_tasks" in chunk and "_background_tasks" not in chunk:
                    payload = {"background_tasks": chunk["background_tasks"]}
                elif "_background_tasks" in chunk:
                    payload = {"background_tasks": chunk["_background_tasks"]}
                if "actions" in chunk and "_actions" not in chunk:
                    payload = {"actions": chunk["actions"]}
                elif "_actions" in chunk:
                    payload = {"actions": chunk["_actions"]}
                yield f"data: {json.dumps(payload)}\n\n"
                yield from _yield_completed_audio()
                continue
            
            if not chunk:
                yield from _yield_completed_audio()
                continue
            
            if isinstance(chunk, str):
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                if not tts_enabled:
                    continue
                yield from _yield_completed_audio()
                buffer += chunk
                sentences, buffer = _split_sentences(buffer)
                sentences = _merge_short(sentences)

                if held and sentences and len(sentences[0].split()) <= _MERGE_IF_WORDS:
                    held = (held + " " + sentences[0]).strip()
                    sentences = sentences[1:]

                for i, sent in enumerate(sentences):
                    min_w = _MIN_WORDS_FIRST if is_first else _MIN_WORDS
                    if len(sent.split()) < min_w:
                        continue
                    is_last = (i == len(sentences) - 1)
                    if held:
                        _submit(held)
                        held = None
                        is_first = False
                    if is_last and _should_hold_sentence_for_continuation(sent):
                        held = sent
                    else:
                        _submit(sent)
                        is_first = False

                if buffer and len(buffer.split()) >= _TTS_BUFFER_MIN_WORDS:
                    if time.perf_counter() - last_submit_time > _TTS_BUFFER_TIMEOUT:
                        if held:
                            _submit(held)
                            held = None
                            is_first = False
                        _submit(buffer.strip())
                        buffer = ""
                        is_first = False

                yield from _yield_completed_audio()

    except Exception as e:
        for fut, _ in audio_queue:
            fut.cancel()
        yield f"data: {json.dumps({'chunk': '', 'done': True, 'error': str(e)})}\n\n"
        return

    if tts_enabled:
        remaining = buffer.strip()
        if held:
            if remaining and len(remaining.split()) <= _MERGE_IF_WORDS:
                _submit((held + " " + remaining).strip())
            else:
                _submit(held)
                if remaining:
                    _submit(remaining)
        elif remaining:
            _submit(remaining)
        for fut, sent in audio_queue:
            try:
                audio = fut.result(timeout=15)
                b64 = base64.b64encode(audio).decode("ascii")
                yield f"data: {json.dumps({'audio': b64, 'sentence': sent})}\n\n"
            except FuturesTimeoutError:
                logger.warning("[TTS-INLINE] Timeout for '%s' (15s)", (sent or "")[:40])
            except Exception as exc:
                logger.warning("[TTS-INLINE] Failed for '%s': %s", (sent or "")[:40], exc)

    yield f"data: {json.dumps({'chunk': '', 'done': True, 'session_id': session_id})}\n\n"
