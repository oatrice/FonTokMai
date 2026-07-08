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
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_rain_incoming(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()
    
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
        "endpoint": "tomorrow"
    })
    mock_wm_instance.get_advanced_alerts = AsyncMock(return_value={})

    # Execute
    await check_rain_and_alert()

    # Assertions
    mock_repo.get_active_locations.assert_called_once()
    mock_wm_instance.predict_rain.assert_called_once_with(13.0, 100.0, mock_state=None, location_name="home")
    
    mock_send_msg.assert_called_once()
    call_args, call_kwargs = mock_send_msg.call_args
    assert call_args[0] == 123
    assert "ฝนกำลังเคลื่อนมาทางพิกัด" in call_args[1]
    assert "(ในอีก" in call_args[1]
    assert "Tomorrow.io" in call_args[1]
    
    reply_markup = call_args[2] if len(call_args) > 2 else call_kwargs.get("reply_markup")
    assert reply_markup is not None
    kb = reply_markup["inline_keyboard"]
    assert len(kb) == 4

    mock_repo.update_last_alerted.assert_called_once()


@pytest.mark.asyncio
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_recently_alerted(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Alerted 30 mins ago (cooldown: 120 min ยังไม่หมด)
    # last_alert_max_rain = 1.5 → rain ปัจจุบัน = 1.5 → ไม่เพิ่มขึ้น → ไม่ทะลุบล็อก
    loc1 = UserLocation(
        chat_id=123,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30),
        last_alert_max_rain=1.5,  # ความรุนแรงครั้งล่าสุดเท่ากับปัจจุบัน
    )
    mock_repo.get_active_locations.return_value = [loc1]

    # Rain in 30 mins (same intensity as last alert → Smart Cooldown should NOT override)
    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    rain_time = base_time + timedelta(minutes=30)
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 1.5}
        ],
        "max_rain": 1.5  # เท่าเดิม → ไม่ทะลุบล็อก
    })

    # Execute
    await check_rain_and_alert()

    # Should NOT send message (cooldown, ความรุนแรงไม่เพิ่มขึ้น)
    mock_send_msg.assert_not_called()
    mock_repo.update_last_alerted.assert_not_called()


@pytest.mark.asyncio
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_smart_cooldown_override(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    """
    Issue #26: Smart Cooldown Override
    ถ้าความรุนแรงของฝนปัจจุบัน > ครั้งล่าสุด ควรทะลุ Cooldown และแจ้งเตือนได้ทันที
    """
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()

    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context

    # แจ้งเตือนไปแล้ว 30 นาที (ยังติด cooldown 120 นาที)
    # แต่ครั้งก่อนฝน 2.0 mm/hr, ตอนนี้เจอพายุ 8.0 mm/hr → ทะลุบล็อก!
    loc1 = UserLocation(
        chat_id=456,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30),
        last_alert_max_rain=2.0,
    )
    mock_repo.get_active_locations.return_value = [loc1]
    mock_repo.get_mock_state.return_value = None

    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    rain_time = base_time + timedelta(minutes=10)
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 8.0}
        ],
        "max_rain": 8.0,
        "intensity": "หนักมาก",
        "duration_minutes": 45,
        "wind_speed_kmh": 30.0,
        "endpoint": "tomorrow",
    })

    await check_rain_and_alert()

    # ต้องส่งแจ้งเตือน (Smart Cooldown Override)
    mock_send_msg.assert_called_once()
    call_args, call_kwargs = mock_send_msg.call_args
    assert call_args[0] == 456
    assert "ทวีความรุนแรง" in call_args[1] or "อัปเดต" in call_args[1]
    mock_repo.update_last_alerted.assert_called_once()


@pytest.mark.asyncio
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_no_rain(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()
    
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

@pytest.mark.asyncio
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_all_clear(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Previously alerted
    loc1 = UserLocation(
        chat_id=123,
        name="home",
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30),
        last_alert_max_rain=2.0
    )
    mock_repo.get_active_locations.return_value = [loc1]
    mock_repo.get_mock_state.return_value = None

    mock_wm_instance = mock_weather_mgr_cls.return_value
    base_time = datetime.now(timezone.utc)
    # No rain
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0.0}
        ],
        "max_rain": 0.0
    })

    # Execute
    await check_rain_and_alert()

    # Should send All-Clear message
    mock_send_msg.assert_called_once()
    call_args, call_kwargs = mock_send_msg.call_args
    assert "เคลียร์แล้ว" in call_args[1] or "หยุดตกแล้ว" in call_args[1]
    
    mock_repo.update_last_alerted.assert_called_once()
    call_args, call_kwargs = mock_repo.update_last_alerted.call_args
    assert call_kwargs.get("max_rain") == 0.0

@pytest.mark.asyncio
@patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock)
@patch("app.scheduler_tasks.WeatherManager")
@patch("app.scheduler_tasks.get_repo_context")
@patch("app.scheduler_tasks.fetch_tmd_radar_routine", new_callable=AsyncMock)
@patch("app.scheduler_tasks.MetricsService")
async def test_check_rain_and_alert_with_advanced_alerts(
    mock_metrics,
    mock_tmd_radar,
    mock_get_repo_context,
    mock_weather_mgr_cls,
    mock_send_msg
):
    mock_repo = AsyncMock()
    mock_metrics.return_value = AsyncMock()
    
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
    rain_time = base_time + timedelta(minutes=10)
    
    mock_wm_instance.predict_rain = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0.0},
            {"time": rain_time.isoformat(), "rain": 5.0}
        ],
        "max_rain": 5.0,
        "intensity": "ปานกลาง",
        "duration_minutes": 30,
        "wind_speed_kmh": 15.0,
        "endpoint": "xweather"
    })
    
    # Mock advanced alerts
    mock_wm_instance.get_advanced_alerts = AsyncMock(return_value={
        "advisories": [{"name": "Severe Thunderstorm Warning"}],
        "lightning": {"distance_km": 2.5},
        "stormcell": {"distance_km": 10.0, "max_dbz": 60, "speed_kmh": 40}
    })

    # Execute
    await check_rain_and_alert()

    # Should send TWO messages: one for rain, one for advanced alerts
    assert mock_send_msg.call_count == 2
    
    # Check first message (Rain)
    first_call_args = mock_send_msg.call_args_list[0][0]
    assert "ฝนกำลังเคลื่อนมาทางพิกัด" in first_call_args[1]
    
    # Check second message (Advanced Alerts)
    second_call_args = mock_send_msg.call_args_list[1][0]
    assert "⚠️ ประกาศเตือนภัย: Severe Thunderstorm Warning" in second_call_args[1]
    assert "⚡ ฟ้าผ่าระยะใกล้สุด: 2.5 กม." in second_call_args[1]
    assert "🌪️ ตรวจพบกลุ่มพายุ" in second_call_args[1]

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
        
    secret = "test_cron_secret_scheduler"
    with patch("app.routers.scheduler.CRON_SECRET", secret):
        with patch("app.routers.scheduler.CloudTasksService.enqueue_task", new_callable=AsyncMock, return_value="projects/my-project/locations/asia/queues/my-queue/tasks/12345") as mock_enqueue:
            with TestClient(app) as test_client:
                response = test_client.post("/api/v1/cron/check-rain", headers={"X-Cron-Secret": secret})
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_enqueue.assert_called_once_with("worker/check-rain", {})

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
