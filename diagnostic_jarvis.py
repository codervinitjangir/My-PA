import os, sys, json, time
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

print("=== DIAGNOSTIC 1: AgentRouter Config ===")
key = os.getenv("AGENTROUTER_API_KEY", "")
url = os.getenv("AGENTROUTER_BASE_URL", "")
fast = os.getenv("GPT_FAST_MODEL", "")
deep = os.getenv("DEEP_MODEL", "")
print("API Key loaded:", key[:6] + "..." if key else "MISSING")
print("Base URL:", url)
print("GPT_FAST_MODEL:", fast)
print("DEEP_MODEL:", deep)

print()
print("=== DIAGNOSTIC 2: Gemini Keys Loaded ===")
for name in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
    k = os.getenv(name, "")
    print(f"  {name}: {'loaded (' + k[:8] + '...)' if k else 'MISSING'}")

print()
print("=== DIAGNOSTIC 3: Google Token / Calendar ===")
token_path = "database/google_token.json"
exists = os.path.exists(token_path)
print("google_token.json exists locally:", exists)
if exists:
    print("File size:", os.path.getsize(token_path), "bytes")
g_b64 = os.getenv("GOOGLE_TOKEN_B64", "")
print("GOOGLE_TOKEN_B64 in env:", ("set (" + str(len(g_b64)) + " chars)") if g_b64 else "NOT SET")
is_cloud = os.getenv("ENV", "") == "production" or os.getenv("RENDER", "") != ""
print("IS_CLOUD:", is_cloud)

print()
print("=== ISOLATED TEST: AgentRouter gpt-5.5 ===")
try:
    import openai
    client = openai.OpenAI(base_url=url, api_key=key, timeout=30.0, max_retries=0)
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=fast or "gpt-5.5",
        messages=[{"role": "user", "content": "Reply with exactly: AgentRouter Tier2 OK"}],
        max_tokens=20,
        temperature=0
    )
    elapsed = time.perf_counter() - t0
    text = resp.choices[0].message.content
    print("STATUS: SUCCESS")
    print("Response:", text)
    print("Time:", round(elapsed, 2), "s")
except Exception as e:
    err_str = str(e)
    print("STATUS: FAILED")
    print("Error type:", type(e).__name__)
    print("Error body:", err_str[:500])

print()
print("=== ISOLATED TEST: AgentRouter claude-opus-4-8 ===")
try:
    client2 = openai.OpenAI(base_url=url, api_key=key, timeout=30.0, max_retries=0)
    t0 = time.perf_counter()
    resp2 = client2.chat.completions.create(
        model=deep or "claude-opus-4-8",
        messages=[{"role": "user", "content": "Reply with exactly: AgentRouter Tier3 OK"}],
        max_tokens=20,
        temperature=0
    )
    elapsed2 = time.perf_counter() - t0
    text2 = resp2.choices[0].message.content
    print("STATUS: SUCCESS")
    print("Response:", text2)
    print("Time:", round(elapsed2, 2), "s")
except Exception as e:
    err_str = str(e)
    print("STATUS: FAILED")
    print("Error type:", type(e).__name__)
    print("Error body:", err_str[:500])

print()
print("=== ISOLATED TEST: Gemini (Key 1) ===")
try:
    from google import genai
    g_key = os.getenv("GEMINI_API_KEY", "")
    gclient = genai.Client(api_key=g_key)
    t0 = time.perf_counter()
    gres = gclient.models.generate_content(model="gemini-2.0-flash", contents="Reply with exactly: Gemini Tier1 OK")
    elapsed3 = time.perf_counter() - t0
    print("STATUS: SUCCESS")
    print("Response:", gres.text[:100])
    print("Time:", round(elapsed3, 2), "s")
except Exception as e:
    print("STATUS: FAILED")
    print("Error:", str(e)[:300])

print()
print("Done.")
