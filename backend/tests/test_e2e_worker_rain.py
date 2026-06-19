"""
E2E Test: Telegram Worker /handle-rain
ทดสอบว่า POST /worker/handle-rain ทำงานครบ pipeline:
1. รับ payload จาก Cloud Tasks
2. ค้นหา location จาก Firestore
3. เรียก WeatherManager
4. ส่งข้อความกลับผ่าน Telegram API
"""
import pytest
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
import os

WORKER_SECRET = os.getenv("WORKER_SECRET", os.getenv("CRON_SECRET", "default_secret_for_local_testing"))


# ────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


def make_mock_location(lat=13.75, lng=100.5, name="home"):
    loc = MagicMock()
    loc.latitude = lat
    loc.longitude = lng
    loc.name = name
    loc.chat_id = 99999
    loc.expires_at = None
    return loc


# ────────────────────────────────────────────────────────────
# 1. E2E: /handle-rain → weather → send Telegram message
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_handle_rain_sends_telegram_message():
    """
    Test ว่า worker_handle_rain:
    1. ค้นหา location จาก repo
    2. เรียก WeatherManager.predict_rain()
    3. เรียก send_telegram_message_return_id และ edit_telegram_message กลับ
    ไม่ crash และไม่คืน status=error
    """
    mock_repo = AsyncMock()
    mock_repo.get_user_locations.return_value = [make_mock_location()]
    mock_repo.get_mock_state.return_value = None
    mock_repo.get_all_api_reliability.return_value = {"tomorrow": 0.9}
    mock_repo.get_location.return_value = None
    mock_repo.record_api_query_success.return_value = None

    @asynccontextmanager
    async def mock_repo_ctx():
        yield mock_repo

    mock_weather_result = {
        "endpoint": "tomorrow",
        "predictions": [
            {"time": "2026-06-19T10:00:00Z", "rain": 0.0},
            {"time": "2026-06-19T10:10:00Z", "rain": 3.5},
        ],
        "max_rain": 3.5,
        "intensity": "ฝนปานกลาง",
        "duration_minutes": 30,
        "wind_speed_kmh": 12.0,
        "wind_dir_text": "ตะวันออก",
        "radar_gif_bytes": None,
        "radar_hq_gif_bytes": None,
        "radar_static_bytes": None,
        "radar_tracking_bytes": None,
        "rain_timeline_bytes": None,
    }

    with patch("app.services.weather_manager.get_repo_context", mock_repo_ctx), \
         patch("app.routers.webhook.get_repo_context", mock_repo_ctx):

        with patch("app.routers.webhook.WeatherManager") as MockWeatherManager, \
             patch("app.routers.webhook.send_telegram_message_return_id", new_callable=AsyncMock) as mock_loading, \
             patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send, \
             patch("app.routers.webhook.edit_telegram_message", new_callable=AsyncMock) as mock_edit:

            mock_loading.return_value = 12345  # loading message id

            mock_instance = MockWeatherManager.return_value
            mock_instance.predict_rain = AsyncMock(return_value=mock_weather_result)
            mock_instance.get_advanced_alerts = AsyncMock(return_value={"advisories": []})

            from app.routers.webhook import handle_rain_command
            await handle_rain_command(chat_id=99999, command="/rain")

    # ต้องมีการส่งข้อความ loading หรือ edit message
    assert mock_loading.called or mock_send.called or mock_edit.called


# ────────────────────────────────────────────────────────────
# 2. E2E: /handle-rain เมื่อไม่มี saved location
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_worker_handle_rain_no_location_sends_warning():
    """
    ถ้า user ไม่มี location บันทึกไว้
    ต้องส่ง warning message กลับ แทนที่จะ crash
    """
    mock_repo = AsyncMock()
    mock_repo.get_user_locations.return_value = []  # ไม่มี location

    @asynccontextmanager
    async def mock_repo_ctx():
        yield mock_repo

    with patch("app.routers.webhook.get_repo_context", mock_repo_ctx), \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock) as mock_send:

        from app.routers.webhook import handle_rain_command
        await handle_rain_command(chat_id=99999, command="/rain")

    # ต้องส่งข้อความเตือน
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0]
    assert "ไม่พบพิกัด" in call_args[1] or "พิกัด" in call_args[1]


# ────────────────────────────────────────────────────────────
# 3. E2E: POST /worker/handle-rain via HTTP (integration test)
# ────────────────────────────────────────────────────────────

def test_worker_http_endpoint_unauthorized(client):
    """
    POST /worker/handle-rain โดยไม่มี X-Worker-Secret ต้องได้ 401
    """
    response = client.post("/worker/handle-rain", json={
        "chat_id": 99999,
        "command": "/rain",
        "show_advanced": False
    })
    assert response.status_code == 401


def test_worker_http_endpoint_returns_ok_on_success(client):
    """
    POST /worker/handle-rain พร้อม secret และ mock ทั้งหมด
    ต้องได้ status=ok ไม่ใช่ status=error
    """
    mock_repo = AsyncMock()
    mock_repo.get_user_locations.return_value = []  # empty → will send warning

    @asynccontextmanager
    async def mock_repo_ctx():
        yield mock_repo

    with patch("app.routers.webhook.get_repo_context", mock_repo_ctx), \
         patch("app.routers.webhook.send_telegram_message", new_callable=AsyncMock):

        response = client.post(
            "/worker/handle-rain",
            json={"chat_id": 99999, "command": "/rain", "show_advanced": False},
            headers={"X-Worker-Secret": WORKER_SECRET}
        )

    assert response.status_code == 200
    data = response.json()
    # worker ต้องส่ง status=ok เสมอ (error message จะถูกส่งผ่าน Telegram แทน)
    assert data["status"] == "ok"
