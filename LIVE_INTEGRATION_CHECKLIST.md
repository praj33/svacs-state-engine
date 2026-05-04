# Live Integration Checklist

## Current Status

- State Engine HTTP receiver is ready.
- Selected transport: HTTP push.
- Endpoint during live test: `<active-ngrok-url>/ingest/intelligence`.
- Health check: `<active-ngrok-url>/health`.
- Nupur's signal/perception evidence is available and summarized in `samples/upstream_readiness_summary.json`.
- Ankita's intelligence schema is compatible with State Engine input.
- `validation_status` is accepted and preserved in audit logs, but not included in `state_event`.

## Before Ankita Tests

1. Start State Engine:

```powershell
uvicorn api_server:app --host 0.0.0.0 --port 9000
```

2. Start ngrok:

```powershell
ngrok http 9000
```

3. Confirm health:

```powershell
Invoke-RestMethod -Uri <active-ngrok-url>/health -Headers @{ "ngrok-skip-browser-warning" = "true" }
```

4. Send Ankita:

```text
POST <active-ngrok-url>/ingest/intelligence

Headers:
Content-Type: application/json
ngrok-skip-browser-warning: true
```

## Request Format

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

## Expected Response Format

```json
{
  "trace_id": "9d6dc7d6-d915-4738-a3bf-f20c78f6780b",
  "vessel_type": "cargo",
  "risk_level": "MEDIUM",
  "state": "WARNING",
  "anomaly_flag": false,
  "timestamp": "2026-05-04T09:38:01.262978+00:00",
  "short_label": "Watch"
}
```

## Required Live Cases

- cargo
- speedboat
- submarine
- low confidence
- anomaly

## Evidence To Capture

- Request `intelligence_event` for each case
- Returned `state_event` for each case
- State Engine audit logs from `logs/live_bucket.jsonl`
- Stage trace logs from Nupur and Ankita for:
  - signal
  - perception
  - NICAI
  - validation
  - intelligence
  - state_engine

## Completion Rule

Final Phase 5 is complete only when the same `trace_id` is visible across all stages for all 5 live cases.
