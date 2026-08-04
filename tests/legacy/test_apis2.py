import sys
import os
from openai import OpenAI
from config import *

def test_agentrouter_models():
    print("\n=== Testing AgentRouter Models ===")
    
    models = ["gpt-4o-mini", "gpt-4o", "claude-3-opus-20240229", "gpt-5.5", "claude-opus-4-8"]
    
    client = OpenAI(
        api_key=AGENTROUTER_API_KEY,
        base_url=AGENTROUTER_BASE_URL,
        timeout=10.0
    )

    for model in models:
        print(f"Testing Model '{model}'...")
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            print(f"  [SUCCESS] Model '{model}' works!")
        except Exception as e:
            print(f"  [FAILED] Model '{model}': {type(e).__name__} - {e}")

if __name__ == '__main__':
    test_agentrouter_models()
