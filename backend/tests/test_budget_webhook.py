import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import base64
import json

from app.main import app

client = TestClient(app)

def create_pubsub_payload(data_dict: dict) -> dict:
    json_str = json.dumps(data_dict)
    b64_str = base64.b64encode(json_str.encode()).decode()
    return {
        "message": {
            "data": b64_str,
            "messageId": "123",
            "publishTime": "2023-01-01T00:00:00Z"
        },
        "subscription": "projects/test/subscriptions/test"
    }

def test_budget_alert_invalid_base64():
    payload = {
        "message": {
            "data": "invalid_base64_!@#",
            "messageId": "123"
        }
    }
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 400
    assert "Invalid Pub/Sub message data" in response.json()["detail"]

@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_warning(mock_send_telegram):
    data = {
        "budgetDisplayName": "Test Budget",
        "alertThresholdExceeded": 0.85,
        "costAmount": 8.5,
        "budgetAmount": 10.0,
        "currencyCode": "USD"
    }
    payload = create_pubsub_payload(data)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "warning_sent"
    mock_send_telegram.assert_called_once()

@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_shutdown_success(mock_send_telegram, mock_revoke):
    mock_revoke.return_value = True
    data = {
        "budgetDisplayName": "Test Budget",
        "alertThresholdExceeded": 1.0,
        "costAmount": 10.0,
        "budgetAmount": 10.0,
        "currencyCode": "USD"
    }
    payload = create_pubsub_payload(data)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "shutdown_success"
    mock_revoke.assert_called_once()
    mock_send_telegram.assert_called_once()
