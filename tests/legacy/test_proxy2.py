import httpx, time

print("=== RAW TEST: Render proxy gpt-5.5 ===")
t0 = time.perf_counter()
r = httpx.post(
    "https://jarvis-mcaj.onrender.com/proxy/agentrouter/v1/chat/completions",
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    json={"model":"gpt-5.5","messages":[{"role":"user","content":"Say: OK"}],"max_tokens":10,"temperature":0,"stream":False},
    timeout=90
)
elapsed = round(time.perf_counter()-t0, 2)
print("HTTP Status:", r.status_code)
print("Content-Type:", r.headers.get("content-type",""))
print("Content-Length:", len(r.content))
print("Raw body (first 500 chars):", repr(r.text[:500]))
print("Time:", elapsed, "s")

if r.status_code == 200 and r.content:
    try:
        data = r.json()
        text = data.get("choices",[{}])[0].get("message",{}).get("content","")
        print("PARSED RESPONSE:", text)
    except Exception as e:
        print("JSON parse error:", e)
