# State Engine

Deterministic backend layer that converts `intelligence_event` into a stable `state_event` for UI and Mitra consumption.

## Pipeline Position

```text
signal -> perception -> NICAI -> Sanskar -> State Engine -> Bucket -> InsightFlow -> UI/Mitra
```

## Responsibility Boundary

- Accept the upstream `intelligence_event` unchanged.
- Preserve the incoming `trace_id`; never generate a new one.
- Map `risk_level` into a deterministic system `state`.
- Force `state=CRITICAL` when `anomaly_flag=True`.
- Emit a minimal downstream `state_event`.

The State Engine does not rewrite upstream explanation text and does not generate user-facing explanation.

## Contracts

### Input: `intelligence_event`

```json
{
  "trace_id": "TRACE-001",
  "vessel_type": "cargo",
  "confidence": 0.94,
  "risk_level": "LOW",
  "anomaly_flag": false,
  "explanation": "Routine cargo route with no hostile indicators."
}
```

### Output: `state_event`

```json
{
  "trace_id": "TRACE-001",
  "vessel_type": "cargo",
  "risk_level": "LOW",
  "state": "NORMAL",
  "anomaly_flag": false,
  "timestamp": "2026-04-29T00:00:00+00:00",
  "short_label": "Safe"
}
```

## Locked Mapping

| `risk_level` | `state` |
|---|---|
| `LOW` | `NORMAL` |
| `MEDIUM` | `WARNING` |
| `HIGH` | `ALERT` |
| `CRITICAL` | `CRITICAL` |

Override rule:

```text
anomaly_flag=True -> state=CRITICAL
```

## Files

| File | Responsibility |
|---|---|
| `state_engine.py` | Deterministic mapping from intelligence to state |
| `trace_validator.py` | Explicit trace validation and continuity enforcement |
| `bucket_logger.py` | Append-only JSONL audit logs |
| `schemas/state_event.py` | Pydantic contracts for input/output/log entries |
| `main.py` | Five-scenario integration demo and sample export |
| `tests/test_state_engine.py` | Locked mapping, trace, and logging tests |

## Quick Start

```bash
pip install -r requirements.txt
python main.py
pytest tests/ -v
```

Running `python main.py` exports:

- `samples/state_engine_runs.json`
- `samples/trace_continuity_proof.json`
- `samples/bucket_logs.jsonl`

## Failure Policy

- Invalid or missing `trace_id` raises an explicit error after logging `trace_error`.
- Any trace mismatch across the pipeline raises an explicit error.
- No silent failures.
