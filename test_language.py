import sys
import os

# Fix console encoding for Hindi chars on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import get_system_prompt
from app.providers.groq_provider import GroqProvider

def test_language():
    print("Testing Language Responses (using GroqProvider)...\n")
    try:
        provider = GroqProvider(None)
    except Exception as e:
        print(f"Failed to init GroqProvider: {e}")
        return
    
    # 1. Hinglish Test
    hinglish_prompt = "yaar mera calendar check karo"
    print(f"User: {hinglish_prompt}")
    res = provider.get_response(hinglish_prompt, None)
    print(f"JARVIS: {res}\n")
    
    # 2. Pure Hindi Test
    hindi_prompt = "कृपया मुझे कल का मौसम बताएं।"
    print(f"User: {hindi_prompt}")
    res = provider.get_response(hindi_prompt, None)
    print(f"JARVIS: {res}\n")
    
    # 3. English Test
    english_prompt = "What is 2 + 2?"
    print(f"User: {english_prompt}")
    res = provider.get_response(english_prompt, None)
    print(f"JARVIS: {res}\n")

if __name__ == '__main__':
    test_language()
