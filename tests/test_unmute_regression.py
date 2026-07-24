"""
tests/test_unmute_regression.py — Regression Test for Volume Unmute Classification Precedence Bug

Ensures phrases containing "unmute" (e.g. "Unmute sound", "Unmute volume") are never misclassified
as volume_mute due to substring matching precedence.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from app.core.voice.intent_engine import FastPathIntentEngine


@pytest.mark.asyncio
async def test_unmute_intent_precedence():
    engine = FastPathIntentEngine()
    
    test_phrases = ["Unmute sound", "Unmute volume", "unmute pc", "unmute audio"]
    for phrase in test_phrases:
        prediction = await engine.classify_intent(phrase)
        assert prediction.intent_type == "action", f"Failed for phrase: '{phrase}'"
        assert prediction.action == "volume_unmute", f"Phrase '{phrase}' was misclassified as '{prediction.action}'"

if __name__ == "__main__":
    asyncio.run(test_unmute_intent_precedence())
    print("Regression test test_unmute_intent_precedence PASSED!")
