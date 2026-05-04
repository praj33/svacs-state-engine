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

## Live HTTP Intake

Run the State Engine receiver:

```bash
uvicorn api_server:app --host 0.0.0.0 --port 9000
```

Upstream NICAI/Sanskar can push live intelligence output here:

```text
POST http://localhost:9000/ingest/intelligence
```

Expected request body:

```json
{
  "trace_id": "9d6dc7d6-d915-4738-a3bf-f20c78f6780b",
  "vessel_type": "cargo",
  "confidence": 0.6396,
  "risk_level": "MEDIUM",
  "anomaly_flag": false,
  "explanation": "Moderate confidence acoustic detection - medium risk",
  "validation_status": "ALLOW"
}
```

The response is the deterministic `state_event`. Extra upstream fields such as `validation_status` are preserved in audit logs, but are not forwarded to UI/Mitra state output.

Running `python main.py` exports:

- `samples/state_engine_runs.json`
- `samples/trace_continuity_proof.json`
- `samples/bucket_logs.jsonl`

## Failure Policy

- Invalid or missing `trace_id` raises an explicit error after logging `trace_error`.
- Any trace mismatch across the pipeline raises an explicit error.
- No silent failures.
