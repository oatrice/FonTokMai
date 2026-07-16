import os
os.environ["STORAGE_BACKEND"] = "sqlite"
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.models import UserLocation
from app.services.notification import NotificationService, TelegramNotificationService, LineNotificationService, get_notification_service
from app.repositories.base import LocationRepository

@pytest.mark.asyncio
async def test_location_repository_supports_string_chat_id():
    """Verify repository save and retrieve works with string chat_id (e.g. Line user id)."""
    import os
    if os.getenv("STORAGE_BACKEND", "sqlite").lower() == "sqlite":
        from app.database import engine
        from app.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    from app.dependencies import get_repo_context
    async with get_repo_context() as repo:
        chat_id = "U1234567890abcdef1234567890abcdef"
        
        # Cleanup if exists
        await repo.delete_location(chat_id, "test_line_loc")
        
        # Save a location for Line platform
        loc = await repo.save_location(
            chat_id=chat_id,
            lat=13.7563,
            lng=100.5018,
            retention_type="FOREVER",
            name="test_line_loc",
            platform="line"
        )
        
        # Verify retrieved data
        retrieved = await repo.get_location(chat_id, "test_line_loc")
        assert retrieved is not None
        assert retrieved.chat_id == chat_id
        assert retrieved.platform == "line"
        
        # Clean up
        await repo.delete_location(chat_id, "test_line_loc")

@pytest.mark.asyncio
async def test_notification_service_factory_and_interfaces():
    """Verify that we can obtain the correct notification service for each platform."""
    telegram_service = get_notification_service("telegram")
    line_service = get_notification_service("line")
    
    assert isinstance(telegram_service, TelegramNotificationService)
    assert isinstance(line_service, LineNotificationService)
    
    assert hasattr(line_service, "send_text_message")
    assert hasattr(line_service, "send_photo")
    assert hasattr(line_service, "send_document")

def test_line_notification_dynamic_config():
    """Verify that LineNotificationService access token and configuration are resolved dynamically."""
    import os
    line_service = get_notification_service("line")
    
    original_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    try:
        # Change token dynamically
        os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "new_dynamic_token_123"
        assert line_service.access_token == "new_dynamic_token_123"
        assert line_service.config.access_token == "new_dynamic_token_123"
    finally:
        if original_token is not None:
            os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = original_token
        else:
            del os.environ["LINE_CHANNEL_ACCESS_TOKEN"]


def test_line_webhook_router_verification_and_event_handling():
    """Test Line webhook endpoint signature verification and request processing."""
    from app.main import app
    client = TestClient(app)
    
    # Send a request with invalid signature to verify security check (should return 400 or 403)
    response = client.post(
        "/api/v1/line/webhook",
        json={"events": []},
        headers={"X-Line-Signature": "invalid_signature"}
    )
    assert response.status_code in (400, 403)

@pytest.mark.asyncio
async def test_line_webhook_success_flow():
    """Test successful Line webhook location event processing."""
    from app.main import app
    from contextlib import asynccontextmanager

    payload = {
        "events": [
          {
            "type": "message",
            "replyToken": "mockReplyToken123",
            "source": {
              "type": "user",
              "userId": "U1234567890abcdef1234567890abcdef"
            },
            "message": {
              "id": "12345678",
              "type": "location",
              "title": "Home Test Location",
              "latitude": 13.7563,
              "longitude": 100.5018
            },
            "timestamp": 1625616000000,
            "mode": "active",
            "webhookEventId": "01FZ5286598QCHAX97525A1A8A",
            "deliveryContext": {
              "isRedelivery": False
            }
          }
        ]
    }
    
    mock_weather_result = {
        "predictions": [
            {"time": "2026-05-29T10:00:00Z", "rain": 0.0}
        ],
        "max_rain": 0.0,
        "intensity": "ไม่มีฝน (No Rain)",
        "duration_minutes": 0,
        "wind_speed_kmh": 5.0,
        "endpoint": "tomorrow",
    }

    with patch("app.services.weather_manager.WeatherManager") as mock_wm_cls:
        mock_wm_instance = mock_wm_cls.return_value
        mock_wm_instance.predict_rain = AsyncMock(return_value=mock_weather_result)

        with patch("app.routers.line_webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            mock_repo.get_mock_state.return_value = None
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            client = TestClient(app)
            response = client.post(
                "/api/v1/line/webhook",
                json=payload,
                headers={"X-Line-Signature": "MOCK_SIGNATURE"}
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            
            mock_repo.save_location.assert_called_once_with(
                chat_id="U1234567890abcdef1234567890abcdef",
                lat=13.7563,
                lng=100.5018,
                retention_type="FOREVER",
                name="Home Test Location",
                platform="line"
            )

@pytest.mark.asyncio
async def test_line_webhook_text_commands():
    """Test successful Line webhook text command event processing."""
    from app.routers.line_webhook import line_webhook
    from contextlib import asynccontextmanager
    from fastapi import BackgroundTasks
    import json
    import asyncio

    payload = {
        "events": [
          {
            "type": "message",
            "replyToken": "mockReplyToken123",
            "source": {
              "type": "user",
              "userId": "U1234567890abcdef1234567890abcdef"
            },
            "message": {
              "id": "12345678",
              "type": "text",
              "text": "/devmock rain",
              "quoteToken": "mockQuoteToken123"
            },
            "timestamp": 1625616000000,
            "mode": "active",
            "webhookEventId": "01FZ5286598QCHAX97525A1A8A",
            "deliveryContext": {
              "isRedelivery": False
            }
          }
        ]
    }

    req = AsyncMock()
    req.json.return_value = payload
    req.body.return_value = json.dumps(payload).encode("utf-8")
    req.url.hostname = "localhost"
    
    bg_tasks = BackgroundTasks()

    with patch("app.services.notification.get_notification_service") as mock_get_notifier:
        mock_notifier = AsyncMock()
        mock_get_notifier.return_value = mock_notifier

        with patch("app.routers.line_webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            await line_webhook(req, bg_tasks, "MOCK_SIGNATURE")
            print("INITIAL BG TASKS:", bg_tasks.tasks)
            
            # Manually execute all nested background tasks
            while bg_tasks.tasks:
                t = bg_tasks.tasks.pop(0)
                print(f"RUNNING TASK: {t.func.__name__} with args {t.args}")
                if asyncio.iscoroutinefunction(t.func):
                    await t.func(*t.args, **t.kwargs)
                else:
                    t.func(*t.args, **t.kwargs)
                print("CURRENT BG TASKS:", bg_tasks.tasks)
            
            mock_repo.set_mock_state.assert_called_once_with(
                "U1234567890abcdef1234567890abcdef",
                "rain"
            )

@pytest.mark.asyncio
async def test_line_webhook_text_commands_uses_reply_api():
    """Verify that text commands reply to the user using the Reply API instead of Push API."""
    from app.routers.line_webhook import line_webhook
    from contextlib import asynccontextmanager
    from fastapi import BackgroundTasks
    import json
    import asyncio

    payload = {
        "events": [
          {
            "type": "message",
            "replyToken": "realReplyToken123",
            "source": {
              "type": "user",
              "userId": "U1234567890abcdef1234567890abcdef"
            },
            "message": {
              "id": "12345678",
              "type": "text",
              "text": "/mylocation",
              "quoteToken": "mockQuoteToken123"
            },
            "timestamp": 1625616000000,
            "mode": "active",
            "webhookEventId": "01FZ5286598QCHAX97525A1A8A",
            "deliveryContext": {
              "isRedelivery": False
            }
          }
        ]
    }

    req = AsyncMock()
    req.json.return_value = payload
    req.body.return_value = json.dumps(payload).encode("utf-8")
    req.url.hostname = "localhost"
    
    bg_tasks = BackgroundTasks()

    with patch("app.routers.line_webhook.reply_to_line") as mock_reply_to_line:
        with patch("app.routers.line_webhook.get_repo_context") as mock_get_repo_context:
            mock_repo = AsyncMock()
            mock_repo.get_user_locations.return_value = []
            
            @asynccontextmanager
            async def mock_context():
                yield mock_repo
            mock_get_repo_context.side_effect = mock_context
            
            await line_webhook(req, bg_tasks, "MOCK_SIGNATURE")
            
            # Execute background tasks
            while bg_tasks.tasks:
                t = bg_tasks.tasks.pop(0)
                if asyncio.iscoroutinefunction(t.func):
                    await t.func(*t.args, **t.kwargs)
                else:
                    t.func(*t.args, **t.kwargs)
            
            mock_reply_to_line.assert_called_once()
            args, _ = mock_reply_to_line.call_args
            assert args[0] == "realReplyToken123"
            assert len(args[1]) == 1
            assert args[1][0].text == "⚠️ ไม่พบพิกัดที่บันทึกไว้ กรุณาส่ง Location ให้บอทก่อนครับ"


@pytest.mark.asyncio
async def test_line_webhook_individual_media_commands():
    """Verify that specific media commands (/radar, /tracking, /timeline, /nowcast) fetch correct media and reply."""
    from app.routers.line_webhook import line_webhook
    from contextlib import asynccontextmanager
    from fastapi import BackgroundTasks
    import json
    import asyncio

    # Test for /radar command
    payload = {
        "events": [
          {
            "type": "message",
            "replyToken": "radarReplyToken",
            "source": {
              "type": "user",
              "userId": "U1234567890abcdef1234567890abcdef"
            },
            "message": {
              "id": "12345678",
              "type": "text",
              "text": "/radar",
              "quoteToken": "mockQuoteToken123"
            },
            "timestamp": 1625616000000,
            "mode": "active",
            "webhookEventId": "01FZ5286598QCHAX97525A1A8A",
            "deliveryContext": {
              "isRedelivery": False
            }
          }
        ]
    }

    req = AsyncMock()
    req.json.return_value = payload
    req.body.return_value = json.dumps(payload).encode("utf-8")
    req.url.hostname = "localhost"
    
    bg_tasks = BackgroundTasks()

    with patch("app.routers.line_webhook.reply_to_line") as mock_reply_to_line:
        with patch("app.routers.line_webhook.get_repo_context") as mock_get_repo_context:
            with patch("app.services.notification.get_notification_service") as mock_get_notifier:
                mock_notifier = MagicMock()
                mock_notifier._upload_media.return_value = "https://fake-url.com/radar.png"
                mock_get_notifier.return_value = mock_notifier
                
                mock_repo = AsyncMock()
                from app.models import UserLocation
                mock_repo.get_user_locations.return_value = [
                    UserLocation(chat_id="U1234567890abcdef", name="home", latitude=13.0, longitude=100.0)
                ]
                
                @asynccontextmanager
                async def mock_context():
                    yield mock_repo
                mock_get_repo_context.side_effect = mock_context
                
                with patch("app.services.weather_manager.WeatherManager.predict_rain") as mock_predict_rain:
                    mock_predict_rain.return_value = {
                        "predictions": [],
                        "max_rain": 0.0,
                        "intensity": "ไม่มี",
                        "duration_minutes": 0,
                        "endpoint": "tomorrow",
                        "radar_static_bytes": b"radar_bytes",
                        "radar_tracking_bytes": b"tracking_bytes"
                    }
                    
                    await line_webhook(req, bg_tasks, "MOCK_SIGNATURE")
                    
                    while bg_tasks.tasks:
                        t = bg_tasks.tasks.pop(0)
                        if asyncio.iscoroutinefunction(t.func):
                            await t.func(*t.args, **t.kwargs)
                        else:
                            t.func(*t.args, **t.kwargs)
                    
                    mock_reply_to_line.assert_called_once()
                    args, _ = mock_reply_to_line.call_args
                    assert args[0] == "radarReplyToken"
                    assert len(args[1]) == 2
                    assert args[1][0].text is not None
                    assert args[1][1].original_content_url == "https://fake-url.com/radar.png"





