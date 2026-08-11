"""
Self-directed JARVIS audit — dynamic tests with real assertions.
Run against a live server (default http://127.0.0.1:8001).
"""
import asyncio
import json
import os
import sys
import tempfile
import time
import uuid
import wave
import struct
import urllib.request
import urllib.error

BASE = os.getenv("AUDIT_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
RESULTS = []


def auth_headers():
    try:
        from config import JARVIS_API_KEY
        import os
        token = os.getenv("JARVIS_API_TOKEN", "").strip() or "testkey"
        hdrs = {"Authorization": f"Bearer {token}", "X-JARVIS-Token": token}
        if JARVIS_API_KEY:
            hdrs["X-API-Key"] = JARVIS_API_KEY
        return hdrs
    except Exception:
        return {"Authorization": "Bearer testkey", "X-JARVIS-Token": "testkey"}


def record(name, sent, expected, actual, passed):
    RESULTS.append({
        "name": name,
        "sent": sent,
        "expected": expected,
        "actual": actual,
        "pass": passed,
    })
    status = "PASS" if passed else "FAIL"
    print(f"\n[{status}] {name}")
    print(f"  sent: {sent!r}")
    print(f"  expected: {expected!r}")
    print(f"  actual: {actual!r}")


def http_json(method, path, body=None, headers=None, timeout=120):
    url = f"{BASE}{path}"
    data = None
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(auth_headers())
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        try:
            return resp.status, json.loads(raw)
        except json.JSONDecodeError:
            return resp.status, raw


def http_raw(method, path, data=None, headers=None, timeout=120):
    url = f"{BASE}{path}"
    hdrs = auth_headers()
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def stream_jarvis(message, session_id=None):
    body = {"message": message, "session_id": session_id, "tts": False}
    url = f"{BASE}/chat/jarvis/stream"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    chunks = []
    activities = []
    actions = {}
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if "chunk" in obj and obj["chunk"]:
                chunks.append(obj["chunk"])
            if "activity" in obj:
                activities.append(obj["activity"])
            if "actions" in obj:
                actions.update(obj["actions"])
    return "".join(chunks), activities, actions


def test_health():
    status, data = http_json("GET", "/health")
    passed = status == 200 and isinstance(data, dict) and data.get("status") == "ok"
    record("health endpoint", "GET /health", {"status": 200, "body.status": "ok"}, {"status": status, "body": data}, passed)


def test_malformed_chat():
    url = f"{BASE}/chat"
    req = urllib.request.Request(
        url,
        data=b"not-json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        record("malformed JSON body", "POST /chat not-json", "4xx error", "200 unexpected success", False)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        passed = 400 <= e.code < 500
        record("malformed JSON body", "POST /chat not-json", "4xx client error", {"code": e.code, "body": body[:300]}, passed)


def test_invalid_session_id():
    try:
        http_json("POST", "/chat", {"message": "hello", "session_id": "../../../etc/passwd"})
        record("path traversal session_id", "session_id=../../../etc/passwd", "400 ValueError", "no error raised", False)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        passed = e.code == 400 and "Invalid session_id" in body
        record("path traversal session_id", "session_id=../../../etc/passwd", "400 Invalid session_id", {"code": e.code, "body": body[:300]}, passed)


def test_brain_routes():
    cases = [
        ("hello there", "casual_chat", lambda acts, text: True),
        ("what is 2 plus 2", "general", lambda acts, text: any(x in text for x in ["4", "four"])),
        ("who is the current president of the united states", "realtime", lambda acts, text: len(text) > 20),
        ("open youtube", "task", lambda acts, text: bool(acts.get("wopens") or acts.get("plays") or "youtube" in text.lower())),
        ("play despacito", "task", lambda acts, text: bool(acts.get("plays"))),
        ("check my emails", "task", lambda acts, text: "mail" in text.lower() or "email" in text.lower() or bool(acts)),
        ("what's on my calendar today", "task", lambda acts, text: "calendar" in text.lower() or "event" in text.lower() or "schedule" in text.lower()),
    ]
    for msg, route_hint, validator in cases:
        text, activities, actions = stream_jarvis(msg)
        routes = [a.get("route") for a in activities if a.get("event") == "routing"]
        route = routes[0] if routes else None
        passed = route == route_hint and validator(actions, text)
        record(
            f"brain route {route_hint}",
            msg,
            f"route={route_hint}, valid response/actions",
            {"route": route, "text_preview": text[:200], "actions": actions},
            passed,
        )


def test_memory_remember_and_contradiction():
    sid = str(uuid.uuid4())
    # Store initial fact
    t1, a1, _ = stream_jarvis("remember that my favorite color is blue", sid)
    passed_store = "noted" in t1.lower() or "stored" in t1.lower() or "memory" in t1.lower()
    record("memory store remember", "remember that my favorite color is blue", "confirmation stored", t1[:300], passed_store)

    # Contradicting fact should ask for confirmation, not silently overwrite
    t2, a2, _ = stream_jarvis("remember that my favorite color is red", sid)
    passed_conflict = any(w in t2.lower() for w in ["conflict", "update", "differently", "previously", "should i"])
    record(
        "memory contradiction gate",
        "remember that my favorite color is red",
        "asks to confirm update",
        t2[:400],
        passed_conflict,
    )

    # Decline update
    t3, _, _ = stream_jarvis("no", sid)
    passed_decline = "discard" in t3.lower() or "kept" in t3.lower() or "okay" in t3.lower()
    record("memory decline update", "no", "keeps old memory message", t3[:300], passed_decline)


def test_laptop_client_handler_mismatch():
    """Root laptop_client.py vs server action names — static contract check."""
    import importlib.util
    from pathlib import Path
    root = Path("laptop_client.py").read_text(encoding="utf-8")
    server_actions = {"lock_screen", "capture_screen", "scroll", "open_app"}
    missing = []
    for action in server_actions:
        if action == "capture_screen" and "screenshot" in root and "capture_screen" not in root:
            missing.append("capture_screen (server) vs screenshot (client)")
        elif action == "lock_screen" and action not in root:
            missing.append("lock_screen")
        elif action == "scroll" and "elif action == \"scroll\"" not in root:
            missing.append("scroll handler")
    record(
        "root laptop_client action contract",
        "compare server actions to laptop_client.py handlers",
        "all server actions implemented in root laptop_client",
        missing or "all present",
        len(missing) == 0,
    )


def test_task_executor_lock_message_bug():
    from app.services.task_executor import TaskExecutor
    from app.services.decision_types import INTENT_OPEN

    te = TaskExecutor(groq_service=None)
    res = te.execute([(INTENT_OPEN, {"url": "system:scroll_down"})], [])
    # Bug: any system: action sets 'Locked your PC screen.'
    passed = "scroll" in res.text.lower() or "scrolled" in res.text.lower()
    record(
        "task_executor scroll response text",
        "execute scroll_down",
        "mentions scroll, not lock",
        res.text,
        passed,
    )


def test_action_broker_return_type():
    from app.services.action_broker import ActionBroker
    out = ActionBroker.dispatch("nonexistent_tool_xyz", {}, confirmed=True)
    passed = isinstance(out, tuple) and len(out) == 3
    record("ActionBroker.dispatch return type", "dispatch fake tool", "3-tuple", repr(out), passed)


def test_tts():
    status, body, headers = http_raw("POST", "/tts", data=json.dumps({"text": "Audit test one two."}).encode(), headers={"Content-Type": "application/json"})
    passed = status == 200 and len(body) > 500 and "audio" in headers.get("Content-Type", headers.get("content-type", ""))
    record("TTS endpoint", "POST /tts short phrase", "audio/mpeg bytes > 500", {"status": status, "bytes": len(body), "ctype": headers.get("Content-Type")}, passed)


def test_stt_empty():
    # Generate tiny silent wav
    buf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    buf.close()
    with wave.open(buf.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<h", 0) * 1600)
    with open(buf.name, "rb") as f:
        data = f.read()
    os.unlink(buf.name)
    url = f"{BASE}/stt"
    boundary = "----auditboundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="silent.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            record("STT silent audio", "POST /stt silent wav", "422 or empty speech error", {"status": 200, "body": raw[:200]}, False)
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", errors="replace")
        passed = e.code in (422, 400) and ("speech" in body_txt.lower() or "empty" in body_txt.lower() or "short" in body_txt.lower())
        record("STT silent audio", "POST /stt silent wav", "422/400 speech detection failure", {"code": e.code, "body": body_txt[:300]}, passed)


def test_websocket_offline():
    from app.websocket_manager import LaptopConnectionManager
    mgr = LaptopConnectionManager()
    resp = mgr.send_and_wait("lock_screen")
    passed = resp.get("status") == "error" and "offline" in resp.get("message", "").lower()
    record("websocket laptop offline", "send_and_wait lock_screen no client", "error Laptop is offline", resp, passed)


def main():
    print(f"AUDIT BASE URL: {BASE}")
    t0 = time.time()
    test_health()
    test_malformed_chat()
    test_invalid_session_id()
    test_laptop_client_handler_mismatch()
    test_task_executor_lock_message_bug()
    test_action_broker_return_type()
    test_websocket_offline()
    test_tts()
    test_stt_empty()
    test_memory_remember_and_contradiction()
    test_brain_routes()

    passed = sum(1 for r in RESULTS if r["pass"])
    failed = len(RESULTS) - passed
    print("\n" + "=" * 60)
    print(f"AUDIT SUMMARY: {passed} passed, {failed} failed, {len(RESULTS)} total, {time.time()-t0:.1f}s")
    print("=" * 60)
    out_path = "audit_dynamic_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)
    print(f"Wrote {out_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
