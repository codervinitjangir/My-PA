import sys
import os
import httpx
from config import *
from app.providers.groq_provider import GroqProvider

def test_groq_keys():
    print("=== Testing Groq Keys ===")
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage
    
    for i, key in enumerate(GROQ_API_KEYS):
        print(f"Testing Groq Key {i+1}...")
        try:
            llm = ChatGroq(groq_api_key=key, model_name=GROQ_MODEL, max_retries=0, request_timeout=5)
            res = llm.invoke([HumanMessage(content="Hi")])
            print(f"  [SUCCESS] Key {i+1} works!")
        except Exception as e:
            print(f"  [FAILED] Key {i+1}: {type(e).__name__} - {e}")

def test_agentrouter_models():
    print("\n=== Testing AgentRouter Models ===")
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    
    models = ["gpt-4o-mini", "gpt-4o", "claude-3-opus-20240229", "gpt-5.5", "claude-opus-4-8"]
    
    for model in models:
        print(f"Testing Model '{model}'...")
        try:
            llm = ChatOpenAI(
                api_key=AGENTROUTER_API_KEY,
                base_url=AGENTROUTER_BASE_URL,
                model=model,
                max_retries=0,
                request_timeout=10
            )
            res = llm.invoke([HumanMessage(content="Hi")])
            print(f"  [SUCCESS] Model '{model}' works!")
        except Exception as e:
            print(f"  [FAILED] Model '{model}': {type(e).__name__} - {e}")

if __name__ == '__main__':
    test_groq_keys()
    test_agentrouter_models()
