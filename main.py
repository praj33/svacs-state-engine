"""
State Engine — Main Entry Point
================================
CLI runner that demonstrates the full pipeline with sample events.

Usage:
    python main.py              # run demo with sample events
    python main.py event.json   # process a single event from file
"""

from __future__ import annotations

import json
import sys
import logging

from schemas.state_event import IntelligenceEvent, StateEvent, TraceError
from state_engine import StateEngine

# Configure logging so InsightFlow emitter output is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Sample intelligence events for demo
# ---------------------------------------------------------------------------
SAMPLE_EVENTS = [
    # 1. Normal LOW risk
    {
        "trace_id": "TRACE-001-ACOU-SAM-NIC-SAN",
        "vessel_type": "cargo",
        "confidence": 0.92,
        "risk_level": "LOW",
        "anomaly_flag": False,
        "explanation": "Routine cargo vessel on standard shipping lane.",
    },
    # 2. HIGH risk with anomaly
    {
        "trace_id": "TRACE-002-ACOU-SAM-NIC-SAN",
        "vessel_type": "tanker",
        "confidence": 0.87,
        "risk_level": "HIGH",
        "anomaly_flag": True,
        "explanation": "AIS transponder switched off in restricted zone.",
    },
    # 3. Missing trace_id -- should be REJECTED
    {
        "trace_id": None,
        "vessel_type": "fishing",
        "confidence": 0.55,
        "risk_level": "MEDIUM",
        "anomaly_flag": False,
        "explanation": "Unidentified fishing vessel near EEZ boundary.",
    },
    # 4. CRITICAL risk
    {
        "trace_id": "TRACE-004-ACOU-SAM-NIC-SAN",
        "vessel_type": "submarine",
        "confidence": 0.99,
        "risk_level": "CRITICAL",
        "anomaly_flag": True,
        "explanation": "Submerged contact detected -- acoustic signature unknown.",
    },
    # 5. Low confidence event
    {
        "trace_id": "TRACE-005-ACOU-SAM-NIC-SAN",
        "vessel_type": "unknown",
        "confidence": 0.15,
        "risk_level": "LOW",
        "anomaly_flag": False,
        "explanation": "Weak acoustic return -- likely noise or biologics.",
    },
]


def run_demo() -> None:
    """Process sample events and display results."""
    engine = StateEngine()
    print("=" * 72)
    print("  STATE ENGINE -- Demo Run")
    print("  Pipeline: Acoustic -> Samachar -> NICAI -> Sanskar -> STATE -> Bucket")
    print("=" * 72)

    for i, raw in enumerate(SAMPLE_EVENTS, 1):
        print(f"\n{'-' * 72}")
        print(f"  Event #{i}")
        print(f"{'-' * 72}")

        event = IntelligenceEvent(**raw)
        result = engine.process(event)

        if isinstance(result, StateEvent):
            print(f"  [OK] STATE ASSIGNED")
            print(f"     trace_id   : {result.trace_id}")
            print(f"     vessel     : {result.vessel_type}")
            print(f"     risk_level : {result.risk_level.value}")
            print(f"     state      : {result.state.value}")
            print(f"     confidence : {result.confidence}")
            print(f"     anomaly    : {result.anomaly_flag}")
            print(f"     timestamp  : {result.timestamp}")
        elif isinstance(result, TraceError):
            print(f"  [REJECTED] TRACE ERROR -- event rejected")
            print(f"     reason     : {result.error}")

    print(f"\n{'=' * 72}")
    print("  Bucket log written to: logs/bucket.jsonl")
    print(f"{'=' * 72}\n")


def run_single(path: str) -> None:
    """Process a single event from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    engine = StateEngine()
    event = IntelligenceEvent(**raw)
    result = engine.process(event)

    if isinstance(result, StateEvent):
        print(result.json(indent=2))
    else:
        print(json.dumps(result.dict(), indent=2))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single(sys.argv[1])
    else:
        run_demo()
