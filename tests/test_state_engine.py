"""
State Engine - Test Suite
=========================
Validates the locked transformation contract:
  1. risk_level -> state mapping
  2. anomaly override -> CRITICAL
  3. trace_id preservation and explicit failures
  4. stable state_event output for UI and Mitra
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.state_event import IntelligenceEvent, RiskLevel, StateEvent, SystemState
from state_engine import StateEngine
from trace_validator import (
    TraceContinuityError,
    TraceValidationError,
    ensure_trace_chain,
    validate_trace,
)


@pytest.fixture
def engine(tmp_path):
    """Create an engine instance with a temporary bucket log."""
    log_path = str(tmp_path / "bucket.jsonl")
    return StateEngine(bucket_log_path=log_path)


@pytest.fixture
def bucket_log_path(engine):
    """Return the bucket log path from the engine."""
    return engine.bucket.log_path


def _make_event(**overrides) -> IntelligenceEvent:
    """Helper to build an IntelligenceEvent with sensible defaults."""
    defaults = {
        "trace_id": "TRACE-TEST-001",
        "vessel_type": "cargo",
        "confidence": 0.90,
        "risk_level": "LOW",
        "anomaly_flag": False,
        "explanation": "Test event",
    }
    defaults.update(overrides)
    return IntelligenceEvent(**defaults)


@pytest.mark.parametrize(
    ("risk_level", "expected_state", "expected_label"),
    [
        ("LOW", SystemState.NORMAL, "Safe"),
        ("MEDIUM", SystemState.WARNING, "Watch"),
        ("HIGH", SystemState.ALERT, "Concern"),
        ("CRITICAL", SystemState.CRITICAL, "Threat"),
    ],
)
def test_locked_state_mapping(engine, risk_level, expected_state, expected_label):
    """Each allowed risk level must map to the locked system state."""
    event = _make_event(risk_level=risk_level, trace_id=f"TRACE-{risk_level}")
    result = engine.process(event)

    assert isinstance(result, StateEvent)
    assert result.trace_id == f"TRACE-{risk_level}"
    assert result.risk_level == RiskLevel(risk_level)
    assert result.state == expected_state
    assert result.short_label == expected_label
    assert result.anomaly_flag is False


def test_state_event_contract_is_ui_safe(engine):
    """state_event should only expose the stable downstream fields."""
    result = engine.process(_make_event())

    assert set(result.model_dump(mode="json")) == {
        "trace_id",
        "vessel_type",
        "risk_level",
        "state",
        "anomaly_flag",
        "timestamp",
        "short_label",
    }


def test_anomaly_override_forces_critical(engine):
    """anomaly_flag=True must override the mapped state to CRITICAL."""
    event = _make_event(
        risk_level="LOW",
        anomaly_flag=True,
        trace_id="TRACE-ANOMALY",
    )
    result = engine.process(event)

    assert result.trace_id == "TRACE-ANOMALY"
    assert result.risk_level == RiskLevel.LOW
    assert result.state == SystemState.CRITICAL
    assert result.short_label == "Threat"
    assert result.anomaly_flag is True


def test_low_confidence_does_not_change_mapping(engine):
    """Low confidence passes through the engine without extra decision logic."""
    event = _make_event(
        confidence=0.10,
        vessel_type="unknown",
        risk_level="LOW",
        trace_id="TRACE-LOWCONF",
    )
    result = engine.process(event)

    assert result.trace_id == "TRACE-LOWCONF"
    assert result.vessel_type == "unknown"
    assert result.state == SystemState.NORMAL


def test_missing_trace_id_raises_explicit_error(engine):
    """None trace_id must raise an explicit validation error."""
    with pytest.raises(TraceValidationError, match="trace_id is None"):
        engine.process(_make_event(trace_id=None))


@pytest.mark.parametrize("bad_id", ["", "   ", "\t"])
def test_empty_trace_id_raises_explicit_error(engine, bad_id):
    """Empty or whitespace-only trace_id must raise explicitly."""
    with pytest.raises(TraceValidationError, match="empty/whitespace"):
        engine.process(_make_event(trace_id=bad_id))


def test_deterministic_state_fields(engine):
    """Repeated processing should produce the same logical state fields."""
    event = _make_event(
        risk_level="HIGH",
        trace_id="TRACE-DETERMINISTIC",
        confidence=0.67,
    )

    first = engine.process(event)
    second = engine.process(event)

    assert first.trace_id == second.trace_id
    assert first.risk_level == second.risk_level
    assert first.state == second.state
    assert first.short_label == second.short_label
    assert first.anomaly_flag == second.anomaly_flag
    assert first.vessel_type == second.vessel_type


def test_bucket_logging_captures_input_output_and_stage(engine, bucket_log_path):
    """Bucket logs must capture incoming, outgoing, state_stage, and trace errors."""
    engine.process(_make_event(trace_id="TRACE-BUCKET-OK"))

    with pytest.raises(TraceValidationError):
        engine.process(_make_event(trace_id=None))

    with open(bucket_log_path, encoding="utf-8") as fh:
        lines = [json.loads(line) for line in fh if line.strip()]

    log_types = [entry["log_type"] for entry in lines]

    assert "incoming" in log_types
    assert "outgoing" in log_types
    assert "state_stage" in log_types
    assert "trace_error" in log_types

    state_stage_entries = [entry for entry in lines if entry["log_type"] == "state_stage"]
    assert state_stage_entries[0]["trace_id"] == "TRACE-BUCKET-OK"
    assert state_stage_entries[0]["stage"] == "state_engine"
    assert state_stage_entries[0]["state"] == "NORMAL"


def test_validate_trace_helper():
    """The tuple-based validator remains available for standalone checks."""
    ok, message = validate_trace(_make_event(trace_id="VALID-TRACE"))
    assert ok is True
    assert message == ""

    ok, message = validate_trace(_make_event(trace_id=None))
    assert ok is False
    assert "None" in message


def test_trace_chain_proof_accepts_consistent_pipeline():
    """Full pipeline trace proof should pass when every stage matches."""
    trace_id = "TRACE-CHAIN-001"
    result = ensure_trace_chain(
        [
            ("signal", {"trace_id": trace_id}),
            ("perception", {"trace_id": trace_id}),
            ("nicai", {"trace_id": trace_id}),
            ("sanskar", {"trace_id": trace_id}),
            ("state_engine", {"trace_id": trace_id}),
        ]
    )

    assert result == trace_id


def test_trace_chain_proof_raises_on_mismatch():
    """Trace mismatches must fail loudly instead of silently passing."""
    with pytest.raises(TraceContinuityError, match="trace_id mismatch"):
        ensure_trace_chain(
            [
                ("signal", {"trace_id": "TRACE-A"}),
                ("perception", {"trace_id": "TRACE-B"}),
            ]
        )
