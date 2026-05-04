from __future__ import annotations

import json

from fastapi.testclient import TestClient

import api_server
from state_engine import StateEngine


def _client_with_temp_engine(tmp_path) -> tuple[TestClient, str]:
    log_path = str(tmp_path / "live_bucket.jsonl")
    api_server.engine = StateEngine(bucket_log_path=log_path)
    return TestClient(api_server.app), log_path


def test_health_endpoint(tmp_path):
    client, _ = _client_with_temp_engine(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "stage": "state_engine"}


def test_ingest_intelligence_returns_state_event(tmp_path):
    client, _ = _client_with_temp_engine(tmp_path)
    payload = {
        "trace_id": "9d6dc7d6-d915-4738-a3bf-f20c78f6780b",
        "vessel_type": "cargo",
        "confidence": 0.6396,
        "risk_level": "MEDIUM",
        "anomaly_flag": False,
        "explanation": "Moderate confidence acoustic detection - medium risk",
        "validation_status": "ALLOW",
    }

    response = client.post("/ingest/intelligence", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == payload["trace_id"]
    assert body["vessel_type"] == "cargo"
    assert body["risk_level"] == "MEDIUM"
    assert body["state"] == "WARNING"
    assert body["anomaly_flag"] is False
    assert body["short_label"] == "Watch"
    assert "explanation" not in body
    assert "validation_status" not in body


def test_ingest_intelligence_preserves_upstream_extra_in_logs(tmp_path):
    client, log_path = _client_with_temp_engine(tmp_path)
    payload = {
        "trace_id": "60b833aa-e1b8-4f45-8294-b4b198f87cb7",
        "vessel_type": "speedboat",
        "confidence": 0.3922,
        "risk_level": "HIGH",
        "anomaly_flag": False,
        "explanation": "Low confidence acoustic detection - high risk",
        "validation_status": "ALLOW",
    }

    response = client.post("/ingest/intelligence", json=payload)

    assert response.status_code == 200
    with open(log_path, encoding="utf-8") as fh:
        entries = [json.loads(line) for line in fh if line.strip()]

    incoming = next(entry for entry in entries if entry["log_type"] == "incoming")
    outgoing = next(entry for entry in entries if entry["log_type"] == "outgoing")
    assert incoming["input"]["validation_status"] == "ALLOW"
    assert outgoing["input"]["validation_status"] == "ALLOW"
    assert "validation_status" not in outgoing["output"]


def test_ingest_intelligence_rejects_missing_trace_id(tmp_path):
    client, _ = _client_with_temp_engine(tmp_path)
    payload = {
        "trace_id": None,
        "vessel_type": "unknown",
        "confidence": 0.2721,
        "risk_level": "CRITICAL",
        "anomaly_flag": True,
        "explanation": "Anomalous acoustic pattern detected",
        "validation_status": "ALLOW",
    }

    response = client.post("/ingest/intelligence", json=payload)

    assert response.status_code == 400
    assert "trace_id is None" in response.json()["detail"]
