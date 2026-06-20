import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import base64
import json

client = TestClient(app)

def create_payload(budget_amount=10.0, cost_amount=10.5, alert_threshold=1.0):
    data = {
        "budgetDisplayName": "FonMaYang Budget",
        "alertThresholdExceeded": alert_threshold,
        "costAmount": cost_amount,
        "budgetAmount": budget_amount,
        "currencyCode": "THB"
    }
    encoded_data = base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    return {
        "message": {
            "data": encoded_data,
            "messageId": "1234567890",
            "publishTime": "2026-06-20T00:00:00Z"
        },
        "subscription": "projects/fonmayang/subscriptions/billing-alerts-sub"
    }

@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert")
def test_budget_exceeded_first_time(mock_send, mock_revoke):
    mock_revoke.return_value = "REVOKED"
    payload = create_payload(10.0, 10.5, 1.0)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "shutdown_success"
    mock_revoke.assert_called_once()
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][0]
    assert "Emergency Shutdown" in msg

@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert")
def test_budget_exceeded_already_private(mock_send, mock_revoke):
    mock_revoke.return_value = "ALREADY_PRIVATE"
    payload = create_payload(10.0, 10.5, 1.0)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "already_private"
    mock_revoke.assert_called_once()
    mock_send.assert_not_called()  # Deduplicated!

@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert")
def test_budget_exceeded_error(mock_send, mock_revoke):
    mock_revoke.return_value = "ERROR"
    payload = create_payload(10.0, 10.5, 1.0)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "shutdown_failed"
    mock_revoke.assert_called_once()
    mock_send.assert_called_once()
    msg = mock_send.call_args[0][0]
    assert "Shutdown FAILED" in msg

if __name__ == "__main__":
    pytest.main(["-v", "test_budget_webhook.py"])
