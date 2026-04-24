"""
State Engine — Test Suite
=========================
Covers all required scenarios:
  1. Normal flow (all risk levels)
  2. Missing trace_id
  3. Empty trace_id
  4. Anomaly case
  5. Low confidence case
  6. Determinism guarantee
  7. Bucket logging verification
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.state_event import IntelligenceEvent, StateEvent, TraceError, RiskLevel
from trace_validator import validate_trace
from state_engine import StateEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 1. Normal Flow — all four risk levels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
def test_normal_flow(engine, level):
    """Each risk_level must produce the matching state, with trace_id preserved."""
    event = _make_event(risk_level=level, trace_id=f"TRACE-{level}")
    result = engine.process(event)

    assert isinstance(result, StateEvent)
    assert result.trace_id == f"TRACE-{level}"
    assert result.risk_level == RiskLevel(level)
    assert result.state == RiskLevel(level)          # deterministic mirror
    assert result.vessel_type == "cargo"
    assert result.confidence == 0.90
    assert result.timestamp                          # non-empty


# ---------------------------------------------------------------------------
# 2. Missing trace_id → rejection
# ---------------------------------------------------------------------------

def test_missing_trace_id(engine):
    """None trace_id must be rejected and logged as trace_error."""
    event = _make_event(trace_id=None)
    result = engine.process(event)

    assert isinstance(result, TraceError)
    assert "None" in result.error
    assert result.event_snapshot["trace_id"] is None


# ---------------------------------------------------------------------------
# 3. Empty / whitespace trace_id → rejection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["", "   ", "\t"])
def test_empty_trace_id(engine, bad_id):
    """Empty or whitespace-only trace_id must be rejected."""
    event = _make_event(trace_id=bad_id)
    result = engine.process(event)

    assert isinstance(result, TraceError)
    assert "empty" in result.error.lower() or "whitespace" in result.error.lower()


# ---------------------------------------------------------------------------
# 4. Anomaly case — anomaly_flag passes through correctly
# ---------------------------------------------------------------------------

def test_anomaly_case(engine):
    """anomaly_flag=True must appear in the output state_event unchanged."""
    event = _make_event(
        anomaly_flag=True,
        risk_level="HIGH",
        explanation="AIS transponder off in restricted zone",
    )
    result = engine.process(event)

    assert isinstance(result, StateEvent)
    assert result.anomaly_flag is True
    assert result.state == RiskLevel.HIGH
    assert result.explanation == "AIS transponder off in restricted zone"


# ---------------------------------------------------------------------------
# 5. Low confidence — passes through (no filtering / gating)
# ---------------------------------------------------------------------------

def test_low_confidence(engine):
    """Low confidence must NOT be filtered — it passes through unchanged."""
    event = _make_event(confidence=0.10, risk_level="LOW")
    result = engine.process(event)

    assert isinstance(result, StateEvent)
    assert result.confidence == 0.10
    assert result.state == RiskLevel.LOW


# ---------------------------------------------------------------------------
# 6. Determinism guarantee (same input → identical output, ignoring timestamp)
# ---------------------------------------------------------------------------

def test_determinism(engine):
    """Running the same event twice must produce structurally identical results."""
    event = _make_event(risk_level="CRITICAL", confidence=0.95)

    r1 = engine.process(event)
    r2 = engine.process(event)

    assert isinstance(r1, StateEvent)
    assert isinstance(r2, StateEvent)
    assert r1.trace_id == r2.trace_id
    assert r1.state == r2.state
    assert r1.risk_level == r2.risk_level
    assert r1.confidence == r2.confidence
    assert r1.anomaly_flag == r2.anomaly_flag
    assert r1.explanation == r2.explanation
    assert r1.vessel_type == r2.vessel_type


# ---------------------------------------------------------------------------
# 7. Bucket logging — all event types logged
# ---------------------------------------------------------------------------

def test_bucket_logging(engine, bucket_log_path):
    """Bucket must contain incoming, outgoing, AND trace_error entries."""
    # Good event → incoming + outgoing
    good = _make_event(trace_id="TRACE-BUCKET-OK")
    engine.process(good)

    # Bad event → trace_error
    bad = _make_event(trace_id=None)
    engine.process(bad)

    # Read log lines
    with open(bucket_log_path, encoding="utf-8") as fh:
        lines = [json.loads(l) for l in fh if l.strip()]

    log_types = [entry["log_type"] for entry in lines]

    assert "incoming" in log_types
    assert "outgoing" in log_types
    assert "trace_error" in log_types

    # Every entry must have a timestamp
    for entry in lines:
        assert entry["timestamp"]


# ---------------------------------------------------------------------------
# 8. Trace validator — unit tests (standalone)
# ---------------------------------------------------------------------------

class TestTraceValidator:
    def test_valid(self):
        event = _make_event(trace_id="VALID-123")
        ok, msg = validate_trace(event)
        assert ok is True
        assert msg == ""

    def test_none(self):
        event = _make_event(trace_id=None)
        ok, msg = validate_trace(event)
        assert ok is False
        assert "None" in msg

    def test_empty(self):
        event = _make_event(trace_id="")
        ok, msg = validate_trace(event)
        assert ok is False

    def test_whitespace(self):
        event = _make_event(trace_id="   ")
        ok, msg = validate_trace(event)
        assert ok is False
