import pytest
from unittest.mock import AsyncMock, patch
from app.database import engine, Base, AsyncSessionLocal
from app.repositories.sqlite import SQLiteLocationRepository
from app.routers.webhook_commands import handle_locations_command, handle_rename_command
from app.routers.webhook_callbacks import handle_callback_query
from app.dependencies import get_repo_context

@pytest.mark.asyncio
async def test_locations_command_and_rename():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    chat_id = 998877
    
    # Save a location
    async with get_repo_context() as repo:
        await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", "home")
    
    # Test /locations command
    with patch("app.routers.webhook_commands._reply", new_callable=AsyncMock) as mock_reply:
        with patch("app.routers.webhook_commands.telegram.send_telegram_message", new_callable=AsyncMock) as mock_send:
            await handle_locations_command(chat_id, "/locations")
            assert mock_reply.called or mock_send.called
            call_args = mock_reply.call_args or mock_send.call_args
            text = call_args[0][1]
            assert "home" in text
            assert "Active" in text or "เปิดใช้งาน" in text

    # Test /rename command
    with patch("app.routers.webhook_commands._reply", new_callable=AsyncMock) as mock_reply:
        await handle_rename_command(chat_id, "/rename home condo")
        assert mock_reply.called
        text = mock_reply.call_args[0][1]
        assert "condo" in text
        
        # Verify renamed in DB
        async with get_repo_context() as repo:
            loc = await repo.get_location(chat_id, "condo")
            assert loc is not None
            assert loc.name == "condo"

    # Test Callback query: Snooze 4 hours (loc_snooze_condo_4)
    callback = {
        "id": "cb_1",
        "from": {"id": chat_id},
        "data": "loc_snooze_condo_4",
        "message": {"message_id": 100}
    }
    with patch("app.services.telegram.answer_callback_query", new_callable=AsyncMock):
        with patch("app.dependencies.get_http_client") as mock_client:
            mock_client.return_value.post = AsyncMock()
            await handle_callback_query(callback)
        
    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id, "condo")
        assert loc.is_snoozed is True
        assert loc.snooze_until is not None

    # Test Callback query: Unsnooze (loc_unsnooze_condo)
    callback_un = {
        "id": "cb_2",
        "from": {"id": chat_id},
        "data": "loc_unsnooze_condo",
        "message": {"message_id": 100}
    }
    with patch("app.services.telegram.answer_callback_query", new_callable=AsyncMock):
        with patch("app.dependencies.get_http_client") as mock_client:
            mock_client.return_value.post = AsyncMock()
            await handle_callback_query(callback_un)
        
    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id, "condo")
        assert loc.is_snoozed is False
        assert loc.snooze_until is None

        # Clean up
        await repo.delete_location(chat_id, "condo")
