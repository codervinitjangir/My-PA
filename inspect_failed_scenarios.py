"""
inspect_failed_scenarios.py — Diagnostic Script to Identify Every Failed Validation Scenario
"""

import asyncio
from test_product_validation_suite import VALIDATION_SUITE_SCENARIOS
from app.core.voice.intent_engine import FastPathIntentEngine

async def run_failure_audit():
    intent_engine = FastPathIntentEngine()
    failures = []

    for sc in VALIDATION_SUITE_SCENARIOS:
        sc_id = sc["id"]
        cat = sc["cat"]
        text_input = sc["input"]

        prediction = await intent_engine.classify_intent(text_input)

        is_passed = True
        reason = ""

        if cat == "Command Execution":
            if not (prediction.intent_type == "action" and prediction.action == sc.get("expected_action")):
                is_passed = False
                reason = f"Expected intent='action', action='{sc.get('expected_action')}', got intent='{prediction.intent_type}', action='{prediction.action}'"

        if not is_passed:
            failures.append({
                "scenario_id": sc_id,
                "name": f"Scenario #{sc_id}: {cat} - '{text_input}'",
                "input": text_input,
                "expected": f"intent='action', action='{sc.get('expected_action')}'",
                "actual": f"intent='{prediction.intent_type}', action='{prediction.action}', target='{prediction.target}'",
                "reason": reason
            })

    print(f"Total Failures Found: {len(failures)}")
    for f in failures:
        print(f"\nFailed Test #{f['scenario_id']}:")
        print(f"  Name           : {f['name']}")
        print(f"  Input          : {f['input']}")
        print(f"  Expected       : {f['expected']}")
        print(f"  Actual         : {f['actual']}")
        print(f"  Reason         : {f['reason']}")

if __name__ == "__main__":
    asyncio.run(run_failure_audit())
