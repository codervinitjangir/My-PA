import httpx, time, json

print("=== TEST: Render proxy gpt-5.5 ===")
t0 = time.perf_counter()
try:
    r = httpx.post(
        "https://jarvis-mcaj.onrender.com/proxy/agentrouter/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={"model":"gpt-5.5","messages":[{"role":"user","content":"Reply with exactly: AgentRouter Tier2 OK"}],"max_tokens":20,"temperature":0},
        timeout=90
    )
    elapsed = round(time.perf_counter()-t0, 2)
    print("HTTP Status:", r.status_code)
    print("Time:", elapsed, "s")
    if r.status_code == 200:
        data = r.json()
        text = data.get("choices",[{}])[0].get("message",{}).get("content","")
        print("RESULT: SUCCESS Tier2")
        print("Response:", text)
    else:
        print("RESULT: FAILED")
        print("Body:", r.text[:500])
except Exception as e:
    print("Exception:", str(e)[:300])

print()
print("=== TEST: Render proxy claude-opus-4-8 ===")
t0 = time.perf_counter()
try:
    r2 = httpx.post(
        "https://jarvis-mcaj.onrender.com/proxy/agentrouter/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={"model":"claude-opus-4-8","messages":[{"role":"user","content":"Reply with exactly: AgentRouter Tier3 OK"}],"max_tokens":20,"temperature":0},
        timeout=90
    )
    elapsed2 = round(time.perf_counter()-t0, 2)
    print("HTTP Status:", r2.status_code)
    print("Time:", elapsed2, "s")
    if r2.status_code == 200:
        data2 = r2.json()
        text2 = data2.get("choices",[{}])[0].get("message",{}).get("content","")
        print("RESULT: SUCCESS Tier3")
        print("Response:", text2)
    else:
        print("RESULT: FAILED")
        print("Body:", r2.text[:500])
except Exception as e:
    print("Exception:", str(e)[:300])
