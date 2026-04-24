"""
State Event Schemas
===================
Defines the input contract (IntelligenceEvent), output contract (StateEvent),
trace error model, and bucket log entry — all enforced via Pydantic.

Determinism guarantee:
  risk_level → state is a direct 1:1 mapping with NO dynamic thresholds.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Risk levels exactly matching the upstream contract."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Input Contract — DO NOT CHANGE
# ---------------------------------------------------------------------------

class IntelligenceEvent(BaseModel):
    """
    Incoming event from Ankita / Sanskar.

    Pipeline:  Acoustic Node → Samachar → NICAI → Sanskar → **State Engine**
    """
    trace_id: Optional[str] = None
    vessel_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    anomaly_flag: bool = False
    explanation: str = ""


# ---------------------------------------------------------------------------
# Output Contract
# ---------------------------------------------------------------------------

class StateEvent(BaseModel):
    """
    Outgoing event produced by the State Engine.

    Consumed by:  Bucket → InsightFlow → Dashboard
    """
    trace_id: str
    vessel_type: str
    confidence: float
    risk_level: RiskLevel
    state: RiskLevel          # deterministic mirror of risk_level
    anomaly_flag: bool
    explanation: str
    timestamp: str            # ISO-8601 UTC string


# ---------------------------------------------------------------------------
# Trace Error
# ---------------------------------------------------------------------------

class TraceError(BaseModel):
    """Logged when an event is rejected due to missing / invalid trace_id."""
    error: str
    event_snapshot: Dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# Bucket Log Entry
# ---------------------------------------------------------------------------

class BucketLogEntry(BaseModel):
    """Single line in the bucket JSONL log file."""
    log_type: str             # "incoming" | "outgoing" | "trace_error"
    trace_id: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str
