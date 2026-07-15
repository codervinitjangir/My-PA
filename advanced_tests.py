import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"X-API-Key": "testkey", "Content-Type": "application/json"}

def test_screen():
    print("\n--- Testing E: Screen Awareness ---")
    data = {"action": "analyze_screen"}
    try:
        resp = requests.post(f"{BASE_URL}/operator/action", json=data, timeout=30)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Response: {str(resp.json())[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def test_voice():
    print("\n--- Testing H: Voice Pipeline (Dummy File) ---")
    # Create a dummy small wav file
    with open("dummy.wav", "wb") as f:
        f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    try:
        with open("dummy.wav", "rb") as f:
            files = {"file": ("dummy.wav", f, "audio/wav")}
            resp = requests.post(f"{BASE_URL}/stt", files=files, timeout=30)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_screen()
    test_voice()
