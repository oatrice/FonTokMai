import pytest
from datetime import datetime, timedelta, timezone
from app.database import engine, Base, AsyncSessionLocal
from app.repositories.sqlite import SQLiteLocationRepository
from app.models import UserLocation, PresenceAnswerCache

@pytest.mark.asyncio
async def test_presence_cache_and_policy_fields():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        repo = SQLiteLocationRepository(session)
        chat_id = "presence_user_1"
        
        # 1. Create a location with presence policy defaults
        loc = await repo.save_location(
            chat_id=chat_id,
            lat=13.75,
            lng=100.5,
            retention_type="FOREVER",
            name="office"
        )
        assert loc.name == "office"
        assert loc.presence_policy == "always_ask"
        assert loc.presence_answer_ttl_minutes == 120
        assert loc.default_fallback_policy == "notify"

        # 2. Update presence policy and schedule
        loc.presence_policy = "schedule_based"
        loc.schedule_active_days = "[1,2,3,4,5]" # Mon-Fri
        loc.schedule_active_start = "09:00"
        loc.schedule_active_end = "18:00"
        await session.commit()
        await session.refresh(loc)
        assert loc.presence_policy == "schedule_based"
        assert loc.schedule_active_days == "[1,2,3,4,5]"

        # 3. Test PresenceAnswerCache repository operations
        ans = await repo.set_presence_answer(chat_id, "office", "yes", ttl_minutes=120)
        assert ans is not None
        assert ans.answer == "yes"
        assert ans.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)

        # 4. Get active answer (Cache HIT)
        cached_ans = await repo.get_presence_answer(chat_id, "office")
        assert cached_ans == "yes"

        # 5. Overwrite or test expired answer (Cache MISS)
        # Manually set expires_at in past
        ans.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        await session.commit()

        expired_ans = await repo.get_presence_answer(chat_id, "office")
        assert expired_ans is None

        # Clean up
        await repo.delete_location(chat_id, "office")

from unittest.mock import AsyncMock, patch
from app.routers.webhook_commands import handle_presence_command
from app.routers.webhook_callbacks import handle_callback_query
from app.scheduler_tasks import _send_combined_alerts
from app.dependencies import get_repo_context

@pytest.mark.asyncio
async def test_presence_commands_and_worker_flow():
    chat_id = 112233
    async with get_repo_context() as repo:
        loc = await repo.save_location(chat_id, 13.75, 100.5, "FOREVER", "garden")
        loc.presence_policy = "always_ask"
        if hasattr(repo, "session") and repo.session:
            await repo.session.commit()

    # 1. Test /presence command
    with patch("app.services.telegram.send_telegram_message", new_callable=AsyncMock) as mock_send:
        await handle_presence_command(chat_id, "/presence garden")
        assert mock_send.called
        text = mock_send.call_args[0][1]
        assert "garden" in text
        assert "always_ask" in text

    # 2. Test Callback set policy to always_notify
    callback = {
        "id": "cb_p1",
        "from": {"id": chat_id},
        "data": "set_policy_garden_always_notify",
        "message": {"message_id": 101}
    }
    with patch("app.services.telegram.answer_callback_query", new_callable=AsyncMock):
        with patch("app.dependencies.get_http_client") as mock_client:
            mock_client.return_value.post = AsyncMock()
            await handle_callback_query(callback)

    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id, "garden")
        assert loc.presence_policy == "always_notify"

    # 3. Test Worker decision flow for always_ask with Cache MISS -> Presence Ping sent
    async with get_repo_context() as repo:
        loc.presence_policy = "always_ask"
        if hasattr(repo, "session") and repo.session:
            await repo.session.commit()

    eval_result = [{
        "loc": loc,
        "type": "rain",
        "text": "Rain coming!",
        "max_rain": 4.5,
        "result": {"eta_minutes": 15, "endpoint": "tomorrow"}
    }]

    with patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock) as mock_send_alert:
        sent, errs = await _send_combined_alerts(chat_id, eval_result, datetime.now(timezone.utc))
        assert sent == 1
        assert mock_send_alert.called
        ping_text = mock_send_alert.call_args[0][1]
        assert "ตรวจพบกลุ่มฝนใกล้พิกัด [garden]" in ping_text

    # 4. User answers YES -> cached and triggers full alert
    cb_yes = {
        "id": "cb_p2",
        "from": {"id": chat_id},
        "data": "presence_ans_garden_yes",
        "message": {"message_id": 102}
    }
    with patch("app.services.telegram.answer_callback_query", new_callable=AsyncMock):
        with patch("app.routers.webhook_location.process_telegram_location", new_callable=AsyncMock) as mock_full_alert:
            with patch("app.dependencies.get_http_client") as mock_client:
                mock_client.return_value.post = AsyncMock()
                await handle_callback_query(cb_yes)
                assert mock_full_alert.called

    # 5. Worker run again -> Cache HIT -> sends full alert directly without ping
    with patch("app.scheduler_tasks.send_telegram_message", new_callable=AsyncMock) as mock_send_direct:
        sent, errs = await _send_combined_alerts(chat_id, eval_result, datetime.now(timezone.utc))
        assert sent == 1
        assert mock_send_direct.called
        alert_text = mock_send_direct.call_args[0][1]
        assert "Rain coming!" in alert_text

    # Clean up
    async with get_repo_context() as repo:
        await repo.delete_location(chat_id, "garden")
