# State Engine

A lightweight, deterministic evaluation layer that converts intelligence events into system state with full trace_id continuity across the SVACS pipeline.

## Pipeline Position

```
Acoustic Node → Samachar → NICAI → Sanskar → STATE ENGINE → Bucket → InsightFlow → Dashboard
```

## Architecture

| Module | Responsibility |
|---|---|
| `schemas/state_event.py` | Pydantic v2 models (IntelligenceEvent, StateEvent, TraceError, BucketLogEntry) |
| `trace_validator.py` | Validates trace_id presence — rejects None/empty/whitespace |
| `bucket_logger.py` | Mandatory JSONL audit logging (incoming, outgoing, trace errors) |
| `emitter.py` | Passive InsightFlow emission (state, latency, trace_id) |
| `state_engine.py` | Core engine — orchestrates validation → state assignment → logging → emission |
| `main.py` | CLI entry point with demo mode and single-event mode |

## State Mapping

Deterministic 1:1 mapping — no dynamic thresholds, no randomness:

| risk_level | → state |
|---|---|
| `LOW` | `LOW` |
| `MEDIUM` | `MEDIUM` |
| `HIGH` | `HIGH` |
| `CRITICAL` | `CRITICAL` |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo (5 sample events)
python main.py

# Process a single event
python main.py event.json

# Run tests
pytest tests/ -v
```

## Bucket Logs

All events are logged to `logs/bucket.jsonl` in append-only JSONL format:
- `incoming` — raw intelligence_event received
- `outgoing` — state_event produced and emitted
- `trace_error` — event rejected due to invalid trace_id

## Failure Conditions (Hard Boundaries)

- ❌ No calls to RAJYA / SAARTHI
- ❌ No enforcement logic
- ❌ No upstream schema modification
- ❌ No missing trace_id propagation
- ❌ No skipping Bucket logging
