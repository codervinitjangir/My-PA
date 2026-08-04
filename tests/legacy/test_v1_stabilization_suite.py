"""
test_v1_stabilization_suite.py — Verification Suite for v1.0 Production Stabilization Modules
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("STABILIZATION_VERIFY")

from app.core.security.allowlist import is_safe_app_target, is_safe_url
from app.core.config import settings
from app.core.reliability.circuit_breaker import AsyncCircuitBreaker, CircuitBreakerOpenException
from app.utils.phonetic_normalizer import PhoneticNormalizer
from app.core.plugins.spec import PluginV1Spec, PluginMetadata

async def run_stabilization_checks():
    logger.info("=" * 70)
    logger.info("   JARVIS v1.0 STABILIZATION & RELIABILITY MODULE VERIFICATION")
    logger.info("=" * 70)

    # 1. Test Security Allow-List
    safe_notepad, _ = is_safe_app_target("notepad.exe")
    unsafe_cmd, err = is_safe_app_target("cmd.exe /c format c:")
    assert safe_notepad is True, "Allowed app target failed!"
    assert unsafe_cmd is False, "Unsafe app target was not blocked!"
    logger.info("[PASS] Security Allow-List Enforcement Engine verified.")

    # 2. Test Configuration Engine
    assert settings.APP_VERSION == "1.0.0", "Version mismatch!"
    logger.info("[PASS] Pydantic Centralized Configuration Engine verified (Version %s).", settings.APP_VERSION)

    # 3. Test Async Circuit Breaker
    breaker = AsyncCircuitBreaker(name="test_api", failure_threshold=2, recovery_timeout_sec=0.5)
    
    async def dummy_failing_api():
        raise RuntimeError("Simulated API 500 error")

    # Fail twice to trip breaker OPEN
    for _ in range(2):
        try:
            await breaker.call(dummy_failing_api)
        except RuntimeError:
            pass

    assert breaker.state == "OPEN", f"Circuit breaker state should be OPEN, got {breaker.state}"
    logger.info("[PASS] Async Circuit Breaker Engine verified (State correctly tripped to OPEN).")

    # 4. Test Phonetic Normalizer
    sample_text = "Opening VS Code to edit JSON files using PyAutoGUI and REST API."
    phonetic_out = PhoneticNormalizer.normalize_for_tts(sample_text)
    assert "Visual Studio Code" in phonetic_out, "Phonetic substitution failed!"
    assert "JAY-sahn" in phonetic_out, "JSON substitution failed!"
    logger.info("[PASS] Tech Acronym Phonetic Normalizer verified.")
    logger.info("       Normalized: '%s'", phonetic_out)

    # 5. Test Plugin API v1.0 Spec
    dummy_plugin = type("DummyPlugin", (), {"metadata": {"name": "test_plugin", "version": "1.0.0", "api_version": "1.0.0"}})
    meta = PluginV1Spec.validate_plugin(dummy_plugin)
    assert meta.name == "test_plugin", "Plugin validation failed!"
    logger.info("[PASS] Plugin API v1.0 Specification Contract verified.")

    print("\n" + "=" * 70)
    print("   *** ALL v1.0 STABILIZATION & RELIABILITY MODULES PASSED ***")

    print("=" * 70 + "\n")

if __name__ == "__main__":
    asyncio.run(run_stabilization_checks())
