import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

from app.scheduler_tasks import check_rain_and_alert
from app.models import UserLocation

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.mark.asyncio
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.get_active_locations', new_callable=AsyncMock)
@patch('app.scheduler_tasks.update_last_alerted_at', new_callable=AsyncMock)
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.AsyncSessionLocal')
async def test_check_rain_and_alert_rain_incoming(
    mock_session_local,
    mock_send_msg,
    mock_update_alerted,
    mock_get_active_locs,
    mock_rainbow_cls
):
    # Setup mock locations
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_get_active_locs.return_value = [loc1]

    # Mock Session context manager
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    # Mock RainbowService
    mock_rainbow_instance = mock_rainbow_cls.return_value
    base_time = datetime.now(timezone.utc)
    # Rain in 30 mins
    rain_time = base_time + timedelta(minutes=30)
    mock_rainbow_instance.predict_rain_by_location = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 1.5}
        ]
    })

    # Execute
    await check_rain_and_alert()

    # Assertions
    mock_get_active_locs.assert_called_once()
    mock_rainbow_instance.predict_rain_by_location.assert_called_once_with(13.0, 100.0)
    mock_send_msg.assert_called_once_with(123, "ฝนกำลังเคลื่อนมาทางทิศของคุณ จะตกหนักที่พิกัดของคุณในอีก 30 นาที\n")
    mock_update_alerted.assert_called_once_with(mock_session, 123)


@pytest.mark.asyncio
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.get_active_locations', new_callable=AsyncMock)
@patch('app.scheduler_tasks.update_last_alerted_at', new_callable=AsyncMock)
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.AsyncSessionLocal')
async def test_check_rain_and_alert_recently_alerted(
    mock_session_local,
    mock_send_msg,
    mock_update_alerted,
    mock_get_active_locs,
    mock_rainbow_cls
):
    # Alerted 30 mins ago
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30)
    )
    mock_get_active_locs.return_value = [loc1]
    
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    # Rain in 30 mins
    mock_rainbow_instance = mock_rainbow_cls.return_value
    base_time = datetime.now(timezone.utc)
    rain_time = base_time + timedelta(minutes=30)
    mock_rainbow_instance.predict_rain_by_location = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0},
            {"time": rain_time.isoformat(), "rain": 1.5}
        ]
    })

    # Execute
    await check_rain_and_alert()

    # Should NOT send message due to 2 hour cooldown
    mock_send_msg.assert_not_called()
    mock_update_alerted.assert_not_called()

@pytest.mark.asyncio
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.get_active_locations', new_callable=AsyncMock)
@patch('app.scheduler_tasks.update_last_alerted_at', new_callable=AsyncMock)
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.AsyncSessionLocal')
async def test_check_rain_and_alert_no_rain(
    mock_session_local,
    mock_send_msg,
    mock_update_alerted,
    mock_get_active_locs,
    mock_rainbow_cls
):
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_get_active_locs.return_value = [loc1]
    
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    mock_rainbow_instance = mock_rainbow_cls.return_value
    base_time = datetime.now(timezone.utc)
    mock_rainbow_instance.predict_rain_by_location = AsyncMock(return_value={
        "predictions": [
            {"time": base_time.isoformat(), "rain": 0}
        ]
    })

    # Execute
    await check_rain_and_alert()

    # Should NOT send message because no rain
    mock_send_msg.assert_not_called()
    mock_update_alerted.assert_not_called()
