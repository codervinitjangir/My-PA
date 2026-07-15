import sys
import os
import asyncio

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import *
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.agentrouter_provider import AgentRouterProvider

def test_groq():
    print("Testing Groq (Tier 4)...")
    try:
        provider = GroqProvider(None)
        res = provider.get_response("Say 'test'", None)
        print("Groq Success:", res)
    except Exception as e:
        print("Groq Failed:", type(e).__name__, e)

def test_gemini():
    print("Testing Gemini (Tier 1)...")
    try:
        provider = GeminiProvider(None)
        res = provider.get_response("Say 'test'", None)
        print("Gemini Success:", res)
    except Exception as e:
        print("Gemini Failed:", type(e).__name__, e)

def test_agentrouter_gpt():
    print(f"Testing AgentRouter {GPT_FAST_MODEL} (Tier 2)...")
    try:
        provider = AgentRouterProvider(None)
        res = next(provider.stream("Say 'test'", GPT_FAST_MODEL, None))
        print("AgentRouter GPT Success:", res)
    except Exception as e:
        print("AgentRouter GPT Failed:", type(e).__name__, e)

def test_agentrouter_claude():
    print(f"Testing AgentRouter {DEEP_MODEL} (Tier 3)...")
    try:
        provider = AgentRouterProvider(None)
        res = next(provider.stream("Say 'test'", DEEP_MODEL, None))
        print("AgentRouter Claude Success:", res)
    except Exception as e:
        print("AgentRouter Claude Failed:", type(e).__name__, e)

if __name__ == '__main__':
    test_gemini()
    print("-" * 40)
    test_agentrouter_gpt()
    print("-" * 40)
    test_agentrouter_claude()
    print("-" * 40)
    test_groq()
