import requests
import json
import time
import uuid

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-API-Key": "testkey", "Content-Type": "application/json"}

def test_chat(session_id, message):
    print(f"\n[USER]: {message}")
    data = {"session_id": session_id, "message": message, "tts": False}
    try:
        resp = requests.post(f"{BASE_URL}/chat", headers=HEADERS, json=data, timeout=30)
        if resp.status_code == 200:
            print(f"[JARVIS]: {resp.json().get('response', '')[:200]}...")
        else:
            print(f"[ERROR {resp.status_code}]: {resp.text}")
        return resp
    except Exception as e:
        print(f"[REQ ERROR]: {e}")
        return None

def main():
    session_id = str(uuid.uuid4())

    print("\n--- Testing A: LLM Router ---")
    test_chat(session_id, "hello, how are you")
    
    long_msg = "Could you please explain the architecture of this system in great detail? " * 5 + "architecture"
    test_chat(session_id, long_msg)

    print("\n--- Testing B: Memory System ---")
    test_chat(session_id, "remember that I prefer dark roast coffee")
    test_chat(session_id, "remember I only drink tea now")
    test_chat(session_id, "my test card is 4111 1111 1111 1111")
    test_chat(session_id, "/forget coffee")

    print("\n--- Testing C: Presets ---")
    test_chat(session_id, "/mode coding")
    test_chat(session_id, "/mode")

    print("\n--- Testing D: Calendar & Gmail ---")
    test_chat(session_id, "what's on my calendar today?")
    test_chat(session_id, "do I have any unread emails?")

    print("\n--- Testing F: Hybrid Remote Actions ---")
    test_chat(session_id, "open notepad")
    test_chat(session_id, "/press win+d")
    test_chat(session_id, "/type this is a test text")

    print("\n--- Testing G: Skill Creator ---")
    test_chat(session_id, "create a tool that returns a random cat fact")
    test_chat(session_id, "yes")
    test_chat(session_id, "create a tool that returns a random dog fact")
    test_chat(session_id, "no")

    print("\n--- Testing J: Multi-Agent Orchestrator ---")
    test_chat(session_id, "compare three different approaches to scaling this system and recommend one")

    print("\n--- Testing Auth & Safety ---")
    try:
        resp = requests.post(f"{BASE_URL}/chat", headers={"Content-Type": "application/json"}, json={"session_id": session_id, "message": "hello"}, timeout=10)
        print(f"[AUTH TEST] Code: {resp.status_code}")
    except Exception as e:
        print(f"[AUTH TEST ERROR]: {e}")

if __name__ == "__main__":
    main()
