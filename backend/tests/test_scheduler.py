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
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_rain_incoming(
    mock_get_repo_context,
    mock_send_msg,
    mock_rainbow_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_repo.get_active_locations.return_value = [loc1]

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
    mock_repo.get_active_locations.assert_called_once()
    mock_rainbow_instance.predict_rain_by_location.assert_called_once_with(13.0, 100.0)
    mock_send_msg.assert_called_once_with(123, "ฝนกำลังเคลื่อนมาทางทิศของคุณ จะตกหนักที่พิกัดของคุณในอีก 30 นาที\n\n📡 เช็คเรดาร์ด้วยตาตัวเอง: https://zoom.earth/maps/radar/#view=13.0,100.0,10z")
    mock_repo.update_last_alerted.assert_called_once()


@pytest.mark.asyncio
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_recently_alerted(
    mock_get_repo_context,
    mock_send_msg,
    mock_rainbow_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    # Alerted 30 mins ago
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=datetime.now() - timedelta(minutes=30)
    )
    mock_repo.get_active_locations.return_value = [loc1]
    
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
    mock_repo.update_last_alerted.assert_not_called()

@pytest.mark.asyncio
@patch('app.scheduler_tasks.RainbowService')
@patch('app.scheduler_tasks.send_telegram_message', new_callable=AsyncMock)
@patch('app.scheduler_tasks.get_repo_context')
async def test_check_rain_and_alert_no_rain(
    mock_get_repo_context,
    mock_send_msg,
    mock_rainbow_cls
):
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_repo
    mock_get_repo_context.side_effect = mock_context
    
    loc1 = UserLocation(
        chat_id=123,
        latitude=13.0,
        longitude=100.0,
        last_alerted_at=None
    )
    mock_repo.get_active_locations.return_value = [loc1]

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
    mock_repo.update_last_alerted.assert_not_called()
