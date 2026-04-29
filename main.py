"""
State Engine - Main Entry Point
===============================
CLI runner that demonstrates deterministic intelligence_event -> state_event
transformation and exports integration artifacts for review.

Usage:
    python main.py              # run the 5-scenario pipeline demo
    python main.py event.json   # process a single intelligence_event file
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from schemas.state_event import IntelligenceEvent, StateEvent
from state_engine import StateEngine
from trace_validator import (
    TraceContinuityError,
    TraceValidationError,
    ensure_trace_chain,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


PIPELINE_SCENARIOS = [
    {
        "name": "cargo",
        "signal_event": {
            "trace_id": "TRACE-CARGO-001",
            "sensor": "hydrophone-07",
            "contact_strength": 0.84,
        },
        "perception_event": {
            "trace_id": "TRACE-CARGO-001",
            "vessel_type": "cargo",
            "confidence": 0.94,
        },
        "nicai_event": {
            "trace_id": "TRACE-CARGO-001",
            "risk_level": "LOW",
            "anomaly_flag": False,
        },
        "intelligence_event": {
            "trace_id": "TRACE-CARGO-001",
            "vessel_type": "cargo",
            "confidence": 0.94,
            "risk_level": "LOW",
            "anomaly_flag": False,
            "explanation": "Routine cargo route with no hostile indicators.",
        },
    },
    {
        "name": "speedboat",
        "signal_event": {
            "trace_id": "TRACE-SPEEDBOAT-002",
            "sensor": "coastal-radar-02",
            "contact_strength": 0.78,
        },
        "perception_event": {
            "trace_id": "TRACE-SPEEDBOAT-002",
            "vessel_type": "speedboat",
            "confidence": 0.88,
        },
        "nicai_event": {
            "trace_id": "TRACE-SPEEDBOAT-002",
            "risk_level": "MEDIUM",
            "anomaly_flag": False,
        },
        "intelligence_event": {
            "trace_id": "TRACE-SPEEDBOAT-002",
            "vessel_type": "speedboat",
            "confidence": 0.88,
            "risk_level": "MEDIUM",
            "anomaly_flag": False,
            "explanation": "Fast coastal movement near a monitored corridor.",
        },
    },
    {
        "name": "submarine",
        "signal_event": {
            "trace_id": "TRACE-SUBMARINE-003",
            "sensor": "sonar-array-11",
            "contact_strength": 0.97,
        },
        "perception_event": {
            "trace_id": "TRACE-SUBMARINE-003",
            "vessel_type": "submarine",
            "confidence": 0.99,
        },
        "nicai_event": {
            "trace_id": "TRACE-SUBMARINE-003",
            "risk_level": "HIGH",
            "anomaly_flag": False,
        },
        "intelligence_event": {
            "trace_id": "TRACE-SUBMARINE-003",
            "vessel_type": "submarine",
            "confidence": 0.99,
            "risk_level": "HIGH",
            "anomaly_flag": False,
            "explanation": "Submerged contact signature matches high-risk profile.",
        },
    },
    {
        "name": "low_confidence",
        "signal_event": {
            "trace_id": "TRACE-LOWCONF-004",
            "sensor": "hydrophone-13",
            "contact_strength": 0.21,
        },
        "perception_event": {
            "trace_id": "TRACE-LOWCONF-004",
            "vessel_type": "unknown",
            "confidence": 0.19,
        },
        "nicai_event": {
            "trace_id": "TRACE-LOWCONF-004",
            "risk_level": "LOW",
            "anomaly_flag": False,
        },
        "intelligence_event": {
            "trace_id": "TRACE-LOWCONF-004",
            "vessel_type": "unknown",
            "confidence": 0.19,
            "risk_level": "LOW",
            "anomaly_flag": False,
            "explanation": "Weak contact retained for monitoring despite low confidence.",
        },
    },
    {
        "name": "anomaly",
        "signal_event": {
            "trace_id": "TRACE-ANOMALY-005",
            "sensor": "ais-fusion-03",
            "contact_strength": 0.91,
        },
        "perception_event": {
            "trace_id": "TRACE-ANOMALY-005",
            "vessel_type": "speedboat",
            "confidence": 0.83,
        },
        "nicai_event": {
            "trace_id": "TRACE-ANOMALY-005",
            "risk_level": "MEDIUM",
            "anomaly_flag": True,
        },
        "intelligence_event": {
            "trace_id": "TRACE-ANOMALY-005",
            "vessel_type": "speedboat",
            "confidence": 0.83,
            "risk_level": "MEDIUM",
            "anomaly_flag": True,
            "explanation": "Unexpected maneuver plus transponder gap detected.",
        },
    },
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _as_dict(model: Any) -> dict[str, Any]:
    dump = getattr(model, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return model.dict()


def _as_json(model: Any) -> str:
    dump_json = getattr(model, "model_dump_json", None)
    if callable(dump_json):
        return dump_json(indent=2)
    return model.json(indent=2)


def _build_trace_chain(
    scenario: dict[str, Any],
    state_event: StateEvent,
) -> list[tuple[str, dict[str, Any]]]:
    return [
        ("signal", scenario["signal_event"]),
        ("perception", scenario["perception_event"]),
        ("nicai", scenario["nicai_event"]),
        ("sanskar", scenario["intelligence_event"]),
        ("state_engine", _as_dict(state_event)),
    ]


def run_demo() -> None:
    """Process the required five scenarios and export review artifacts."""
    bucket_log_path = Path("samples/bucket_logs.jsonl")
    bucket_log_path.parent.mkdir(parents=True, exist_ok=True)
    bucket_log_path.write_text("", encoding="utf-8")

    engine = StateEngine(bucket_log_path=str(bucket_log_path))
    scenario_outputs: list[dict[str, Any]] = []
    trace_proofs: list[dict[str, Any]] = []

    print("=" * 72)
    print("  STATE ENGINE - Deterministic Demo")
    print("  Pipeline: signal -> perception -> NICAI -> Sanskar -> state_engine")
    print("=" * 72)

    for index, scenario in enumerate(PIPELINE_SCENARIOS, start=1):
        intelligence_event = IntelligenceEvent(**scenario["intelligence_event"])
        state_event = engine.process(intelligence_event)
        trace_chain = _build_trace_chain(scenario, state_event)
        trace_id = ensure_trace_chain(trace_chain)
        stage_log = {
            "trace_id": trace_id,
            "stage": "state_engine",
            "state": state_event.state.value,
            "timestamp": state_event.timestamp,
        }

        scenario_outputs.append(
            {
                "scenario": scenario["name"],
                "pipeline": {
                    "signal_event": scenario["signal_event"],
                    "perception_event": scenario["perception_event"],
                    "nicai_event": scenario["nicai_event"],
                    "intelligence_event": scenario["intelligence_event"],
                    "state_event": _as_dict(state_event),
                },
                "state_stage_log": stage_log,
            }
        )
        trace_proofs.append(
            {
                "scenario": scenario["name"],
                "trace_id": trace_id,
                "stages": {
                    stage_name: payload["trace_id"]
                    for stage_name, payload in trace_chain
                },
                "status": "verified",
            }
        )

        print(f"\n{index}. {scenario['name']}")
        print(f"   trace_id   : {trace_id}")
        print(f"   vessel     : {state_event.vessel_type}")
        print(f"   risk_level : {state_event.risk_level.value}")
        print(f"   state      : {state_event.state.value}")
        print(f"   label      : {state_event.short_label}")
        print(f"   anomaly    : {state_event.anomaly_flag}")

    _write_json(Path("samples/state_engine_runs.json"), scenario_outputs)
    _write_json(Path("samples/trace_continuity_proof.json"), trace_proofs)

    print(f"\n{'=' * 72}")
    print("  Sample outputs written to: samples/state_engine_runs.json")
    print("  Trace proof written to   : samples/trace_continuity_proof.json")
    print("  Bucket logs written to   : samples/bucket_logs.jsonl")
    print(f"{'=' * 72}")


def run_single(path: str) -> None:
    """Process a single intelligence_event from a JSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    engine = StateEngine()

    try:
        result = engine.process(IntelligenceEvent(**raw))
        print(_as_json(result))
    except (TraceValidationError, TraceContinuityError) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "event_snapshot": raw,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single(sys.argv[1])
    else:
        run_demo()
