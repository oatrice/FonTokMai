import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from app.scheduler_tasks import check_rain_and_alert
from app.models import UserLocation

@pytest.fixture
def mock_repo_context():
    mock_repo = AsyncMock()
    @asynccontextmanager
    async def get_repo():
        yield mock_repo
    return get_repo, mock_repo

@pytest.mark.asyncio
@patch('app.scheduler_tasks.WeatherManager')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_rain_incoming(
    mock_get_repo_context,
    mock_send_msg,
    mock_weather_mgr_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    loc1 = UserLocation(
        chat_id=123,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_repo.get_active_locations.return_value = [loc1]
    mock_repo.get_mock_state.return_value = None

    # Mock WeatherManager
    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    # Rain in 30 mins
    rain_time = base_time + timedelta(minutes=30)
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 1.5}
        ],
        "max_rain": 1.5,
        "intensity": "ปานกลาง",
        "duration_minutes": 60,
        "wind_speed_kmh": 20.0,
        "endpoint": "tomorrow"
    })

    # Execute
    await check_rain_and_alert()

    # Assertions
    mock_repo.get_active_locations.assert_called_once()
    mock_wm_instance.predict_rain.assert_called_once_with(13.0, 100.0, mock_state=None)
    
    mock_send_msg.assert_called_once()
    call_args, call_kwargs = mock_send_msg.call_args
    assert call_args[0] == 123
    assert "ฝนกำลังเคลื่อนมาทางพิกัด" in call_args[1]
    assert "(ในอีก 30 นาที)" in call_args[1]
    assert "Tomorrow.io" in call_args[1]
    
    reply_markup = call_args[2] if len(call_args) > 2 else call_kwargs.get("reply_markup")
    assert reply_markup is not None
    kb = reply_markup["inline_keyboard"]
    assert len(kb) == 3

    mock_repo.update_last_alerted.assert_called_once()


@pytest.mark.asyncio
@patch('app.scheduler_tasks.WeatherManager')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_recently_alerted(
    mock_get_repo_context,
    mock_send_msg,
    mock_weather_mgr_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Alerted 30 mins ago
    loc1 = UserLocation(
        chat_id=123,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30)
    )
    mock_repo.get_active_locations.return_value = [loc1]
    
    # Rain in 30 mins
    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    rain_time = base_time + timedelta(minutes=30)
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 1.5}
        ],
        "max_rain": 1.5
    })

    # Execute
    await check_rain_and_alert()

    # Should NOT send message due to cooldown
    mock_send_msg.assert_not_called()
    mock_repo.update_last_alerted.assert_not_called()

@pytest.mark.asyncio
@patch('app.scheduler_tasks.WeatherManager')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_no_rain(
    mock_get_repo_context,
    mock_send_msg,
    mock_weather_mgr_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    loc1 = UserLocation(
        chat_id=123,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_repo.get_active_locations.return_value = [loc1]

    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0.1} # < Threshold (0.5)
        ],
        "max_rain": 0.1
    })

    # Execute
    await check_rain_and_alert()

    # Should NOT send message because rain is below threshold
    mock_send_msg.assert_not_called()
    mock_repo.update_last_alerted.assert_not_called()

# --- Endpoint Tests ---
import os
from fastapi.testclient import TestClient

try:
    from app.main import app
    client = TestClient(app)
except ImportError:
    client = None

def test_trigger_rain_check_endpoint_success():
    if not client:
        pytest.fail("FastAPI app is not implemented yet")
        
    secret = os.getenv("CRON_SECRET", "default_secret_for_local_testing")
    with patch("app.routers.scheduler.check_rain_and_alert", new_callable=AsyncMock) as mock_check:
        with TestClient(app) as test_client:
            response = test_client.post("/api/v1/cron/check-rain", headers={"X-Cron-Secret": secret})
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_check.assert_called_once()

def test_trigger_rain_check_endpoint_unauthorized():
    if not client:
        pytest.fail("FastAPI app is not implemented yet")
        
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/cron/check-rain", headers={"X-Cron-Secret": "wrong_secret"})
    
    assert response.status_code == 401

def test_trigger_rain_check_endpoint_missing_header():
    if not client:
        pytest.fail("FastAPI app is not implemented yet")
        
    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/cron/check-rain")
    
    assert response.status_code == 401
