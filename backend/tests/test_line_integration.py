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
