import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def main():
    session_id = str(uuid.uuid4())
    print(f"\n--- Running Deep Test (Session: {session_id}) ---")
    
    # 1. Ask a complex question to trigger deep routing or deep reasoning
    message = "Can you research the complete history of the Apollo space program, summarizing all missions, their primary goals, and key astronauts involved?"
    print(f"[USER]: {message}")
    
    data = {"session_id": session_id, "message": message, "tts": False}
    try:
        resp = requests.post(f"{BASE_URL}/chat", headers={"X-API-Key": "testkey", "Content-Type": "application/json"}, json=data, timeout=60)
        if resp.status_code == 200:
            print(f"[JARVIS]: {resp.json().get('response', '')}")
        else:
            print(f"[ERROR {resp.status_code}]: {resp.text}")
    except Exception as e:
        print(f"[REQ ERROR]: {e}")

if __name__ == "__main__":
    main()
