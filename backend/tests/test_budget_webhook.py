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

@patch("app.routers.budget_webhook.get_repo_context")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_warning(mock_send_telegram, mock_get_repo_context):
    mock_repo = AsyncMock()
    settings_store = {}
    
    async def mock_get_settings():
        return settings_store
    async def mock_set_settings(settings):
        nonlocal settings_store
        settings_store = settings

    mock_repo.get_system_settings.side_effect = mock_get_settings
    mock_repo.set_system_settings.side_effect = mock_set_settings

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context

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


@patch("app.routers.budget_webhook._pause_cloud_scheduler_jobs")
@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_shutdown_success(mock_send_telegram, mock_revoke, mock_pause_sched):
    mock_revoke.return_value = "REVOKED"
    mock_pause_sched.return_value = {}
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

@patch("app.routers.budget_webhook._pause_cloud_scheduler_jobs")
@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_already_private(mock_send_telegram, mock_revoke, mock_pause_sched):
    mock_revoke.return_value = "ALREADY_PRIVATE"
    mock_pause_sched.return_value = {}
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
    assert response.json()["status"] == "already_private"
    mock_revoke.assert_called_once()
    mock_send_telegram.assert_not_called()

@patch("app.routers.budget_webhook._pause_cloud_scheduler_jobs")
@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_already_private_notifies_if_jobs_newly_paused(mock_send_telegram, mock_revoke, mock_pause_sched):
    mock_revoke.return_value = "ALREADY_PRIVATE"
    mock_pause_sched.return_value = {"fonmayang-check-rain": "PAUSED"}
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
    assert response.json()["status"] == "already_private"
    mock_revoke.assert_called_once()
    mock_send_telegram.assert_called_once()
    assert "Cloud Scheduler Suspended" in mock_send_telegram.call_args[0][0]

@patch("app.routers.budget_webhook._pause_cloud_scheduler_jobs")
@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_shutdown_failed(mock_send_telegram, mock_revoke, mock_pause_sched):
    mock_revoke.return_value = "ERROR"
    mock_pause_sched.return_value = {}
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
    assert response.json()["status"] == "shutdown_failed"
    mock_revoke.assert_called_once()
    mock_send_telegram.assert_called_once()

@patch("app.routers.budget_webhook.get_repo_context")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_budget_alert_warning_by_ratio(mock_send_telegram, mock_get_repo_context):
    # Simulate a database state
    mock_repo = AsyncMock()
    settings_store = {}
    
    async def mock_get_settings():
        return settings_store
    async def mock_set_settings(settings):
        nonlocal settings_store
        settings_store = settings

    mock_repo.get_system_settings.side_effect = mock_get_settings
    mock_repo.set_system_settings.side_effect = mock_set_settings
    
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context

    # 1. 85% ratio warning should send a notification and set flag
    data = {
        "budgetDisplayName": "Test Budget",
        "costAmount": 8.5,
        "budgetAmount": 10.0,
        "currencyCode": "USD"
    }
    payload = create_pubsub_payload(data)
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "warning_sent"
    mock_send_telegram.assert_called_once()
    assert settings_store.get("budget_alert_80_sent") is True

    # 2. Duplicate check: sending again should NOT send another notification
    mock_send_telegram.reset_mock()
    response = client.post("/api/v1/internal/budget-alert", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "warning_already_sent"
    mock_send_telegram.assert_not_called()

    # 3. Drop ratio to 50% should reset the flag
    data_dropped = {
        "budgetDisplayName": "Test Budget",
        "costAmount": 5.0,
        "budgetAmount": 10.0,
        "currencyCode": "USD"
    }
    payload_dropped = create_pubsub_payload(data_dropped)
    response = client.post("/api/v1/internal/budget-alert", json=payload_dropped)
    assert response.status_code == 200
    assert settings_store.get("budget_alert_80_sent") is False

@patch("app.routers.budget_webhook.get_repo_context")
@pytest.mark.asyncio
async def test_budget_alert_uses_dev_telegram_bot_token(mock_get_repo_context, monkeypatch):
    mock_repo = AsyncMock()
    mock_repo.get_system_settings.return_value = {}
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context

    monkeypatch.setenv("DEV_TELEGRAM_BOT_TOKEN", "mock_dev_bot_token_999")
    monkeypatch.setenv("DEVELOPER_CHAT_IDS", "12345")

    import respx
    from httpx import Response
    
    with respx.mock:
        route = respx.post("https://api.telegram.org/botmock_dev_bot_token_999/sendMessage").mock(
            return_value=Response(200, json={"ok": True})
        )
        
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
        assert route.called

@patch("app.routers.budget_webhook._pause_cloud_scheduler_jobs")
@patch("app.routers.budget_webhook._revoke_public_access")
@patch("app.routers.budget_webhook._send_telegram_alert", new_callable=AsyncMock)
def test_budget_alert_shutdown_pauses_schedulers(mock_send_telegram, mock_revoke, mock_pause_schedulers):
    mock_revoke.return_value = "REVOKED"
    mock_pause_schedulers.return_value = {"fonmayang-check-rain": "PAUSED"}
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
    mock_pause_schedulers.assert_called_once()
    mock_send_telegram.assert_called_once()
    telegram_text = mock_send_telegram.call_args[0][0]
    assert "Cloud Scheduler:" in telegram_text
    assert "fonmayang-check-rain" in telegram_text

@patch("app.routers.budget_webhook._get_gcp_access_token")
def test_pause_cloud_scheduler_jobs_successfully_pauses_all_configured_jobs(mock_get_token):
    from app.routers.budget_webhook import _pause_cloud_scheduler_jobs
    import respx
    from httpx import Response

    mock_get_token.return_value = "fake-token"

    with respx.mock:
        route = respx.post(url__regex=r"https://cloudscheduler\.googleapis\.com/v1/projects/.*/locations/.*/jobs/.*:pause").mock(
            return_value=Response(200, json={})
        )

        results = _pause_cloud_scheduler_jobs()
        assert isinstance(results, dict)
        assert len(results) > 0
        for job_name, status in results.items():
            assert status == "PAUSED"

@patch("app.routers.budget_webhook._get_gcp_access_token")
def test_pause_cloud_scheduler_jobs_handles_token_exception_gracefully(mock_get_token):
    from app.routers.budget_webhook import _pause_cloud_scheduler_jobs
    mock_get_token.side_effect = Exception("Auth failed")

    results = _pause_cloud_scheduler_jobs()
    assert isinstance(results, dict)
    assert len(results) > 0
    for job_name, status in results.items():
        assert "ERROR: Auth failed" in status




