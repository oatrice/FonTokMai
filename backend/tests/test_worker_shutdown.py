import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager

from app.routers.worker import router as worker_router, WORKER_SECRET

@pytest.fixture
def app():
    _app = FastAPI()
    _app.include_router(worker_router)
    return _app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.mark.asyncio
@patch("app.dependencies.get_repo_context")
async def test_worker_check_rain_blocked_on_emergency_shutdown(mock_get_repo_context, client):
    mock_repo = AsyncMock()
    # Mock settings with emergency_shutdown = True
    mock_repo.get_system_settings.return_value = {"emergency_shutdown": True}
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    headers = {"X-Worker-Secret": WORKER_SECRET}
    response = client.post("/worker/check-rain", headers=headers)
    
    # Verify the request is blocked with 503 Service Unavailable
    assert response.status_code == 503
    assert response.json()["detail"] == "Service suspended due to budget limit exceeded"

@pytest.mark.asyncio
@patch("app.dependencies.get_repo_context")
async def test_worker_check_rain_allowed_if_no_shutdown(mock_get_repo_context, client):
    mock_repo = AsyncMock()
    # Mock settings with emergency_shutdown = False
    mock_repo.get_system_settings.return_value = {"emergency_shutdown": False}
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Mock check_rain_and_alert task to do nothing
    with patch("app.routers.worker.check_rain_and_alert", new_callable=AsyncMock) as mock_check_rain:
        headers = {"X-Worker-Secret": WORKER_SECRET}
        response = client.post("/worker/check-rain", headers=headers)
        
        # Verify the request goes through successfully
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_check_rain.assert_called_once()

@pytest.mark.asyncio
@patch("app.dependencies.get_repo_context")
async def test_worker_bypass_paths_allowed_even_on_shutdown(mock_get_repo_context, client):
    mock_repo = AsyncMock()
    # Mock settings with emergency_shutdown = True
    mock_repo.get_system_settings.return_value = {"emergency_shutdown": True}
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Mock handle_restore_public_access_command
    with patch("app.routers.webhook_admin.handle_restore_public_access_command", new_callable=AsyncMock):
        headers = {"X-Worker-Secret": WORKER_SECRET}
        # /worker/handle-restore-public-access is a bypass path, should NOT return 503
        # It takes LocationPayload or command args. Let's send a mock payload
        payload = {
            "chat_id": 12345,
            "command": "/restore_public_access",
            "username": "test_user"
        }
        response = client.post("/worker/handle-restore-public-access", headers=headers, json=payload)
        
        # Even though emergency_shutdown is True, this bypass path should proceed (returns 200 or executes)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
