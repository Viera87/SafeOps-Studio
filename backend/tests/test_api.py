from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import audit
from main import app


def setup_function() -> None:
    db_path = Path(audit.DB_PATH)
    if db_path.exists():
        db_path.unlink()


client = TestClient(app)


def test_operator_can_preview_and_run_allowed_script() -> None:
    payload = {
        "inputs": {
            "service_name": "nginx",
            "reason": "INC-4421 mitigation",
            "confirm_downtime": True,
        }
    }

    preview = client.post("/api/scripts/restart-service/preview", json=payload)
    assert preview.status_code == 200
    assert preview.json()["status"] == "dry_run"
    assert "Network: none" in preview.json()["output"]

    run = client.post("/api/scripts/restart-service/run", json=payload)
    assert run.status_code == 200
    body = run.json()
    assert body["status"] == "success"
    assert body["exit_code"] == 0
    assert body["redacted_inputs"]["service_name"] == "nginx"


def test_viewer_cannot_run_scripts() -> None:
    response = client.post(
        "/api/scripts/clear-cache/run",
        json={"inputs": {"namespace": "catalog", "ticket_id": "CHG-1001"}},
        headers={"x-safeops-role": "viewer"},
    )

    assert response.status_code == 403
    assert "viewer cannot run" in response.json()["detail"]


def test_admin_only_script_rejects_operator() -> None:
    response = client.post(
        "/api/scripts/database-backup/run",
        json={"inputs": {"database": "billing", "retention_days": 14}},
    )

    assert response.status_code == 403
    assert "operator cannot run database-backup" in response.json()["detail"]


def test_validation_rejects_unknown_and_malformed_inputs() -> None:
    response = client.post(
        "/api/scripts/clear-cache/run",
        json={"inputs": {"namespace": "catalog", "ticket_id": "bad-ticket", "extra": "nope"}},
    )

    assert response.status_code == 422
    assert "invalid format" in response.json()["detail"] or "Unknown input fields" in response.json()["detail"]


def test_admin_can_read_audit_log_after_run() -> None:
    client.post(
        "/api/scripts/clear-cache/run",
        json={"inputs": {"namespace": "catalog", "ticket_id": "CHG-1001"}},
    )

    response = client.get("/api/audit", headers={"x-safeops-role": "admin"})
    assert response.status_code == 200
    assert response.json()[0]["script_id"] == "clear-cache"
    assert response.json()[0]["status"] == "success"


def test_operator_cannot_read_audit_log() -> None:
    response = client.get("/api/audit")

    assert response.status_code == 403
