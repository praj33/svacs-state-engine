"""
Trace Validator
===============
Enforces trace_id continuity across the SVACS pipeline.

Rules:
  - trace_id must be present (not None)
  - trace_id must be non-empty after stripping whitespace
  - If invalid → event is REJECTED and logged as trace_error

This is a pure function — no side effects, no state.
"""

from __future__ import annotations

from typing import Tuple

from schemas.state_event import IntelligenceEvent


def validate_trace(event: IntelligenceEvent) -> Tuple[bool, str]:
    """
    Validate that the intelligence event carries a valid trace_id.

    Returns:
        (True, "")          — trace_id is valid
        (False, reason_str) — trace_id is missing or empty
    """
    if event.trace_id is None:
        return False, "trace_id is None -- event rejected"

    if not event.trace_id.strip():
        return False, "trace_id is empty/whitespace -- event rejected"

    return True, ""
