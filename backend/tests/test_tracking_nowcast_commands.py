"""
Tests for Telegram /tracking and /nowcast commands (Issue #182).
Verifies that /tracking, /tracking <location>, /nowcast, /nowcast <location>
are properly matched by TelegramCommandRouter and dispatch processing logic.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from app.services.command_router import router as cmd_router
import app.routers.webhook_commands  # Registers commands into cmd_router


def make_mock_location(lat=13.75, lng=100.5, name="home"):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lng
    loc.name = name
    loc.chat_id = 99999
    loc.expires_at = None
    return loc


def test_command_router_matches_tracking_and_nowcast():
    """
    Test that cmd_router matches /tracking and /nowcast variants.
    """
    assert cmd_router.match("/tracking") is not None
    assert cmd_router.match("/tracking home") is not None
    assert cmd_router.match("/nowcast") is not None
    assert cmd_router.match("/nowcast home") is not None

    match_tracking = cmd_router.match("/tracking home")
    assert match_tracking[0] == "/tracking"
    assert match_tracking[1]["task_route"] == "worker/handle-rain"

    match_nowcast = cmd_router.match("/nowcast home")
    assert match_nowcast[0] == "/nowcast"
    assert match_nowcast[1]["task_route"] == "worker/handle-rain"


@pytest.mark.asyncio
async def test_handle_tracking_command_execution():
    """
    Test executing handle_rain_command for /tracking and /tracking home.
    """
    from app.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    loc_home = make_mock_location(13.75, 100.5, "home")
    loc_work = make_mock_location(13.80, 100.6, "work")


    mock_repo = AsyncMock()
    mock_repo.get_user_locations.return_value = [loc_home, loc_work]
    mock_repo.get_mock_state.return_value = None
    mock_repo.get_all_api_reliability.return_value = {"tomorrow": 0.9}
    mock_repo.get_location.return_value = None

    @asynccontextmanager
    async def mock_repo_ctx():
        yield mock_repo

    mock_weather_result = {
        "endpoint": "tmd-radar",
        "predictions": [],
        "max_rain": 0.0,
        "intensity": "ไม่มีฝน",
        "duration_minutes": 0,
        "wind_speed_kmh": 10.0,
        "wind_dir_text": "ตะวันออก",
        "radar_gif_bytes": b"gif_bytes",
        "radar_tracking_bytes": b"tracking_bytes",
    }

    with patch("app.services.weather_manager.get_repo_context", mock_repo_ctx), \
         patch("app.dependencies.get_repo_context", mock_repo_ctx):

        with patch("app.services.weather_manager.WeatherManager") as MockWeatherManager, \
             patch("app.services.telegram.send_telegram_message_return_id", new_callable=AsyncMock) as mock_loading, \
             patch("app.services.telegram.send_telegram_photo", new_callable=AsyncMock) as mock_photo, \
             patch("app.services.telegram.send_telegram_document", new_callable=AsyncMock) as mock_doc, \
             patch("app.services.telegram.send_telegram_message", new_callable=AsyncMock) as mock_send:

            mock_loading.return_value = 11111
            mock_instance = MockWeatherManager.return_value
            mock_instance.predict_rain = AsyncMock(return_value=mock_weather_result)

            from app.routers.webhook_commands import handle_rain_command

            # 1. /tracking default location
            await handle_rain_command(chat_id=99999, command="/tracking")
            assert mock_photo.called
            assert mock_doc.called

            mock_photo.reset_mock()
            mock_doc.reset_mock()

            # 2. /tracking work specified location
            await handle_rain_command(chat_id=99999, command="/tracking work")
            assert mock_photo.called
            assert mock_doc.called

            mock_photo.reset_mock()
            mock_doc.reset_mock()

            # 3. /nowcast home specified location
            await handle_rain_command(chat_id=99999, command="/nowcast home")
            assert mock_photo.called
            assert mock_doc.called
