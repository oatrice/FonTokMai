import pytest
from datetime import datetime, timedelta, timezone
from app.database import engine, Base, AsyncSessionLocal
from app.repositories.sqlite import SQLiteLocationRepository
from app.models import UserLocation

@pytest.mark.asyncio
async def test_location_rename_and_snooze():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        repo = SQLiteLocationRepository(session)
        chat_id = "test_user_123"
        
        # 1. Create a location
        loc = await repo.save_location(
            chat_id=chat_id,
            lat=13.7563,
            lng=100.5018,
            retention_type="FOREVER",
            name="home"
        )
        assert loc.name == "home"
        assert loc.is_snoozed is False
        assert loc.snooze_until is None

        # 2. Rename location
        renamed = await repo.rename_location(chat_id, "home", "condo")
        assert renamed is True
        
        old_loc = await repo.get_location(chat_id, "home")
        assert old_loc is None
        
        new_loc = await repo.get_location(chat_id, "condo")
        assert new_loc is not None
        assert new_loc.name == "condo"

        # 3. Snooze location for 2 hours
        snoozed_loc = await repo.snooze_location(chat_id, "condo", hours=2)
        assert snoozed_loc is not None
        assert snoozed_loc.is_snoozed is True
        assert snoozed_loc.snooze_until is not None
        assert snoozed_loc.snooze_until > datetime.now(timezone.utc).replace(tzinfo=None)

        # 4. Check active locations excludes snoozed location
        active = await repo.get_active_locations()
        active_names = [l.name for l in active if l.chat_id == chat_id]
        assert "condo" not in active_names

        # 5. Unsnooze location
        unsnoozed_loc = await repo.unsnooze_location(chat_id, "condo")
        assert unsnoozed_loc is not None
        assert unsnoozed_loc.is_snoozed is False
        assert unsnoozed_loc.snooze_until is None

        # 6. Active locations includes unsnoozed location
        active_after = await repo.get_active_locations()
        active_names_after = [l.name for l in active_after if l.chat_id == chat_id]
        assert "condo" in active_names_after
        
        # Clean up
        await repo.delete_location(chat_id, "condo")
