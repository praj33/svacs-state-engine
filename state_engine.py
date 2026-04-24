"""
State Engine
============
Core deterministic evaluation layer.

Responsibility:
  1. Validate trace_id  (reject if missing)
  2. Assign state        (risk_level → state, 1:1)
  3. Log to Bucket       (incoming, outgoing, errors)
  4. Emit to InsightFlow (passive)

Determinism guarantee:
  Same intelligence_event → identical state_event every time.
  No randomness. No dynamic thresholds. No enforcement logic.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Union

from schemas.state_event import IntelligenceEvent, StateEvent, TraceError
from trace_validator import validate_trace
from bucket_logger import BucketLogger
from emitter import emit_to_insightflow


class StateEngine:
    """Deterministic state assignment engine with trace enforcement."""

    def __init__(self, bucket_log_path: str = "logs/bucket.jsonl") -> None:
        self.bucket = BucketLogger(log_path=bucket_log_path)

    def process(
        self, event: IntelligenceEvent
    ) -> Union[StateEvent, TraceError]:
        """
        Process a single intelligence_event.

        Returns:
            StateEvent  — on success
            TraceError  — if trace_id is missing / invalid
        """
        start = time.monotonic()
        event_dict = event.dict()

        # ── 1. Trace enforcement ──────────────────────────────────
        valid, error_msg = validate_trace(event)

        if not valid:
            # Log the failure to Bucket
            self.bucket.log_trace_error(
                trace_id=event.trace_id,
                event_dict=event_dict,
                error_msg=error_msg,
            )
            return TraceError(
                error=error_msg,
                event_snapshot=event_dict,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # ── 2. Log incoming event ─────────────────────────────────
        self.bucket.log_incoming(
            trace_id=event.trace_id,
            event_dict=event_dict,
        )

        # ── 3. State assignment (deterministic) ───────────────────
        #    risk_level → state  (direct 1:1 mapping, no extra logic)
        now = datetime.now(timezone.utc).isoformat()

        state_event = StateEvent(
            trace_id=event.trace_id,  # type: ignore[arg-type]
            vessel_type=event.vessel_type,
            confidence=event.confidence,
            risk_level=event.risk_level,
            state=event.risk_level,      # ← deterministic mirror
            anomaly_flag=event.anomaly_flag,
            explanation=event.explanation,
            timestamp=now,
        )

        # ── 4. Log outgoing event ─────────────────────────────────
        state_dict = state_event.dict()
        self.bucket.log_outgoing(
            trace_id=state_event.trace_id,
            input_dict=event_dict,
            output_dict=state_dict,
        )

        # ── 5. Passive emission to InsightFlow / Pravah ───────────
        latency_ms = (time.monotonic() - start) * 1000
        emit_to_insightflow(state_event, latency_ms)

        return state_event
