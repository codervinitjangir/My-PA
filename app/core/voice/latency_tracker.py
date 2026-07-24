"""
app/core/voice/latency_tracker.py — Lightweight Production Latency Tracker & Telemetry

Features:
- Records 18 fine-grained metric fields per voice interaction.
- Log rotation (max 10MB, 5 backup log files).
- Queue timing metrics (queue_time_ms).
- Computes rolling P50, P95, and P99 latency statistics.
- Adaptive performance regression detection (flags turns exceeding P95 baseline * 1.5).
- Generates clean console performance summaries and ASCII latency waterfall charts after each interaction.
"""

import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler

from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger("J.A.R.V.I.S.LatencyTracker")

# Log directory configuration
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LATENCY_LOG_FILE = os.path.join(LOGS_DIR, "voice_latency.jsonl")

# Configure rotating file logger (max 10MB per file, 5 backup files)
file_handler = RotatingFileHandler(LATENCY_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(message)s"))

latency_logger = logging.getLogger("VoiceLatencyJSON")
latency_logger.setLevel(logging.INFO)
latency_logger.addHandler(file_handler)
latency_logger.propagate = False


class VoiceMetricsRecord(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    session_id: str = Field(default="voice-session")
    
    # 18 Telemetry fields
    wake_detection_ms: float = 0.0
    recording_duration_ms: float = 0.0
    vad_duration_ms: float = 0.0
    stt_rtt_ms: float = 0.0
    stt_first_partial_ms: float = 0.0
    stt_final_transcript_ms: float = 0.0
    intent_latency_ms: float = 0.0
    desktop_action_latency_ms: float = 0.0
    llm_first_token_ms: float = 0.0
    llm_total_completion_ms: float = 0.0
    sentence_chunk_dispatch_ms: float = 0.0
    tts_first_byte_ms: float = 0.0
    audio_playback_start_ms: float = 0.0
    ttfa_ms: float = 0.0  # Time-To-First-Audio
    total_interaction_time_ms: float = 0.0
    queue_time_ms: float = 0.0  # Queue buffer delay
    cpu_usage_pct: float = 0.0
    ram_usage_mb: float = 0.0
    network_rtt_ms: float = 0.0
    
    is_regression: bool = False
    regression_reasons: List[str] = Field(default_factory=list)


class LatencyTracker:
    """
    Lightweight singleton for voice latency telemetry, rolling percentiles, and regression detection.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LatencyTracker, cls).__new__(cls)
            cls._instance.records: List[VoiceMetricsRecord] = []
            cls._instance._load_recent_history()
        return cls._instance

    def _load_recent_history(self, max_records: int = 200):
        """Load recent history records from disk to populate baseline statistics."""
        if not os.path.exists(LATENCY_LOG_FILE):
            return
            
        try:
            with open(LATENCY_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-max_records:]
                for line in lines:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        self.records.append(VoiceMetricsRecord(**data))
        except Exception as e:
            logger.warning("[LATENCY-TRACKER] Could not load history from disk: %s", e)

    def record_interaction(self, record: VoiceMetricsRecord) -> VoiceMetricsRecord:
        """
        Record interaction telemetry, calculate adaptive regressions, append to rotating JSON log,
        and generate console summary.
        """
        # Get baseline metrics for adaptive regression detection
        baselines = self.get_percentiles()
        
        # Adaptive regression rules (Flag if > 1.5x P95 baseline or SLA ceiling)
        reasons = []
        p95_ttfa = baselines.get("ttfa_ms", {}).get("P95", 1500.0)
        p95_stt = baselines.get("stt_rtt_ms", {}).get("P95", 800.0)
        p95_tts = baselines.get("tts_first_byte_ms", {}).get("P95", 1200.0)

        if record.ttfa_ms > max(2000.0, p95_ttfa * 1.5):
            reasons.append(f"TTFA ({record.ttfa_ms:.1f}ms) breached P95 baseline threshold ({max(2000.0, p95_ttfa * 1.5):.1f}ms)")

        if record.stt_rtt_ms > max(1000.0, p95_stt * 1.5):
            reasons.append(f"STT RTT ({record.stt_rtt_ms:.1f}ms) breached baseline ({max(1000.0, p95_stt * 1.5):.1f}ms)")

        if record.tts_first_byte_ms > max(1200.0, p95_tts * 1.5):
            reasons.append(f"TTS First Byte ({record.tts_first_byte_ms:.1f}ms) breached baseline ({max(1200.0, p95_tts * 1.5):.1f}ms)")

        if reasons:
            record.is_regression = True
            record.regression_reasons = reasons

        # Append to in-memory history & rotating disk log
        self.records.append(record)
        if len(self.records) > 1000:
            self.records = self.records[-1000:]
            
        latency_logger.info(record.model_dump_json())

        # Generate console summary
        self.print_console_summary(record)
        return record

    def get_percentiles(self) -> Dict[str, Dict[str, float]]:
        """Calculate P50, P95, and P99 percentiles across stored interaction turns."""
        if not self.records:
            return {}

        metric_keys = [
            "ttfa_ms", "stt_rtt_ms", "llm_first_token_ms", 
            "sentence_chunk_dispatch_ms", "tts_first_byte_ms", 
            "desktop_action_latency_ms", "total_interaction_time_ms"
        ]

        percentiles_data = {}
        for key in metric_keys:
            values = [getattr(r, key) for r in self.records if getattr(r, key) > 0.0]
            if values:
                percentiles_data[key] = {
                    "P50": float(np.percentile(values, 50)),
                    "P95": float(np.percentile(values, 95)),
                    "P99": float(np.percentile(values, 99)),
                }
            else:
                percentiles_data[key] = {"P50": 0.0, "P95": 0.0, "P99": 0.0}

        return percentiles_data

    def print_console_summary(self, record: VoiceMetricsRecord):
        """Print clean ASCII performance summary and waterfall chart after interaction."""
        stats = self.get_percentiles()
        
        status_flag = "[REGRESSION DETECTED!]" if record.is_regression else "[HEALTHY]"
        
        print("\n" + "=" * 70)
        print(f"      JARVIS TELEMETRY & LATENCY SUMMARY {status_flag}")
        print("=" * 70)
        print(f"  * Session ID            : {record.session_id}")
        print(f"  * Time-To-First-Audio   : {record.ttfa_ms:8.2f} ms  (P50: {stats.get('ttfa_ms', {}).get('P50', 0):.1f}ms | P95: {stats.get('ttfa_ms', {}).get('P95', 0):.1f}ms)")
        print(f"  * STT RTT               : {record.stt_rtt_ms:8.2f} ms  (P50: {stats.get('stt_rtt_ms', {}).get('P50', 0):.1f}ms | P95: {stats.get('stt_rtt_ms', {}).get('P95', 0):.1f}ms)")
        print(f"  * LLM First Token       : {record.llm_first_token_ms:8.2f} ms")
        print(f"  * Sentence Dispatch     : {record.sentence_chunk_dispatch_ms:8.2f} ms")
        print(f"  * TTS First Byte        : {record.tts_first_byte_ms:8.2f} ms")
        print(f"  * Queue Buffer Delay    : {record.queue_time_ms:8.2f} ms")
        print(f"  * Total Turn Duration   : {record.total_interaction_time_ms:8.2f} ms")
        print(f"  * System Load           : CPU {record.cpu_usage_pct:.1f}% | RAM {record.ram_usage_mb:.1f} MB")

        
        print("-" * 70)
        if record.is_regression:
            print("  [!] REGRESSION REASONS:")
            for reason in record.regression_reasons:
                print(f"     - {reason}")
            print("-" * 70)

        print("  STAGE WATERFALL BREAKDOWN:")
        print(f"  1. VAD & Recording    : +{record.recording_duration_ms:6.1f}ms  [{'#' * int(min(20, record.recording_duration_ms / 50))}]")
        print(f"  2. STT Transcription  : +{record.stt_rtt_ms:6.1f}ms  [{'#' * int(min(20, record.stt_rtt_ms / 50))}]")
        print(f"  3. LLM First Token    : +{record.llm_first_token_ms:6.1f}ms  [{'#' * int(min(20, record.llm_first_token_ms / 50))}]")
        print(f"  4. Sentence Dispatch  : +{record.sentence_chunk_dispatch_ms:6.1f}ms  [{'#' * int(min(20, record.sentence_chunk_dispatch_ms / 50))}]")
        print(f"  5. TTS First Byte     : +{record.tts_first_byte_ms:6.1f}ms  [{'#' * int(min(20, record.tts_first_byte_ms / 50))}]")
        print("=" * 70 + "\n")



# Global singleton instance
latency_tracker = LatencyTracker()
