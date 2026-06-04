import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app

client = TestClient(app)

from contextlib import asynccontextmanager

@pytest.fixture
def mock_repo_context():
    mock_repo = AsyncMock()
    
    @asynccontextmanager
    async def get_repo():
        yield mock_repo
        
    return get_repo, mock_repo

def test_telegram_webhook_with_location():
    """
    Issue #37: webhook ต้องส่งข้อความ loading กลับทันที แล้วค่อย process ใน background
    Issue #38: webhook ใช้ WeatherManager แล้ว ไม่ใช่ RainbowService โดยตรง
    """
    mock_weather_result = {
        "predictions": [
            {"time": "2026-05-29T10:00:00Z", "rain": 0.0},
            {"time": "2026-05-29T10:20:00Z", "rain": 2.5}
        ],
        "max_rain": 2.5,
        "intensity": "ปานกลาง",
        "duration_minutes": 30,
        "wind_speed_kmh": 15.0,
        "endpoint": "rainbow-global",
    }

    with patch("app.routers.webhook.WeatherManager") as mock_wm_cls:
        mock_wm_instance = mock_wm_cls.return_value
        mock_wm_instance.predict_rain = AsyncMock(return_value=mock_weather_result)

        with patch("app.routers.webhook.send_telegram_message_return_id", new_callable=AsyncMock) as mock_loading:
            mock_loading.return_value = 999  # simulate returned message_id

            with patch("app.routers.webhook.get_repo_context") as mock_get_repo_context:
                mock_repo = AsyncMock()
                mock_repo.get_location.return_value = None
                mock_repo.get_mock_state.return_value = None

                @asynccontextmanager
                async def mock_context():
                    yield mock_repo
                mock_get_repo_context.side_effect = mock_context

                payload = {
                    "update_id": 12345,
                    "message": {
                        "message_id": 1,
                        "chat": {"id": 9999},
                        "location": {
                            "latitude": 17.1664,
                            "longitude": 104.1486
                        }
                    }
                }

                response = client.post("/api/v1/telegram/webhook", json=payload)

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

            # Issue #37: ต้องส่งข้อความ loading ทันที และส่ง message_id ไปด้วย
            mock_loading.assert_called_once()
            call_args = mock_loading.call_args[0]
            assert call_args[0] == 9999
            assert "กำลังประมวลผล" in call_args[1]

def test_telegram_webhook_without_location():
    """
    Issue #38: ถ้าไม่มี location payload ห้ามเรียก WeatherManager
    """
    with patch("app.routers.webhook.WeatherManager") as mock_wm_cls:
        mock_wm_instance = mock_wm_cls.return_value
        mock_wm_instance.predict_rain = AsyncMock()

        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 2,
                "chat": {"id": 9999},
                "text": "Hello"
            }
        }

        response = client.post("/api/v1/telegram/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}
        mock_wm_instance.predict_rain.assert_not_called()

def test_telegram_webhook_mylocation_cmd():
    with patch("app.routers.webhook.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        
        with patch("app.routers.webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            mock_repo.get_user_locations.return_value = []
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            payload = {
                "update_id": 111,
                "message": {
                    "message_id": 3,
                    "chat": {"id": 8888},
                    "text": "/mylocation"
                }
            }
            response = client.post("/api/v1/telegram/webhook", json=payload)
            assert response.status_code == 200
            assert mock_post.called

def test_telegram_webhook_callback_query_2m():
    with patch("app.routers.webhook.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        
        with patch("app.routers.webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            payload = {
                "update_id": 222,
                "callback_query": {
                    "id": "query_id_123",
                    "from": {"id": 7777},
                    "message": {
                        "message_id": 5,
                        "chat": {"id": 7777}
                    },
                    "data": "loc_save_home_2m_13.75_100.50"
                }
            }
            response = client.post("/api/v1/telegram/webhook", json=payload)
            assert response.status_code == 200
            
            mock_repo.save_location.assert_called_once_with(7777, 13.75, 100.50, "TWO_MONTHS", "home")

def test_telegram_webhook_radar_cmd_with_loc():
    with patch("app.routers.webhook.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        
        with patch("app.routers.webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            from app.models import UserLocation
            loc = UserLocation(chat_id=8888, latitude=13.0, longitude=100.0)
            mock_repo.get_location.return_value = loc
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            payload = {
                "update_id": 112,
                "message": {
                    "message_id": 4,
                    "chat": {"id": 8888},
                    "text": "/radar"
                }
            }
            response = client.post("/api/v1/telegram/webhook", json=payload)
            assert response.status_code == 200
            
            assert mock_post.called
            call_args = mock_post.call_args[1]["json"]
            assert call_args["chat_id"] == 8888
            assert "reply_markup" in call_args
            
            kb = call_args["reply_markup"]["inline_keyboard"]
            assert len(kb) == 3
            assert kb[0][0]["text"] == "📡 Zoom Earth"
            assert kb[0][0]["url"] == "https://zoom.earth/maps/radar/#view=13.0,100.0,10z"
            assert kb[1][0]["text"] == "🌪️ Windy Radar"
            assert kb[1][0]["url"] == "https://www.windy.com/-Weather-radar-radar?radar,13.0,100.0,10"
            assert kb[2][0]["text"] == "🇹🇭 TMD Radar"
            assert kb[2][0]["url"] == "https://weather.tmd.go.th/"
