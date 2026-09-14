import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, UserLocation
from datetime import datetime, timedelta, timezone

# We need an in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# The logic will be in app.services.location
# For TDD, let's assume we have functions in app.services.location:
# save_location(session, chat_id, lat, lng, retention_type)
# get_location(session, chat_id)
# delete_location(session, chat_id)

from app.services.location import save_location, get_location, delete_location

@pytest.mark.asyncio
async def test_save_and_get_location(db_session):
    chat_id = 12345
    lat = 13.7563
    lng = 100.5018
    retention_type = "TWO_MONTHS"
    
    await save_location(db_session, chat_id, lat, lng, retention_type)
    
    loc = await get_location(db_session, chat_id)
    assert loc is not None
    assert str(loc.chat_id) == str(chat_id)
    assert loc.latitude == lat
    assert loc.longitude == lng
    assert loc.retention_type == retention_type
    
    # expires_at should be roughly 60 days from now
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assert loc.expires_at is not None
    diff = loc.expires_at - now
    assert 59 <= diff.days <= 60

@pytest.mark.asyncio
async def test_update_location(db_session):
    chat_id = 9999
    
    # Save first
    await save_location(db_session, chat_id, 10.0, 20.0, "TWO_MONTHS")
    
    # Update
    await save_location(db_session, chat_id, 30.0, 40.0, "FOREVER")
    
    loc = await get_location(db_session, chat_id)
    assert loc.latitude == 30.0
    assert loc.longitude == 40.0
    assert loc.retention_type == "FOREVER"
    assert loc.expires_at is None

@pytest.mark.asyncio
async def test_delete_location(db_session):
    chat_id = 1111
    await save_location(db_session, chat_id, 10.0, 20.0, "TWO_MONTHS")
    
    # Delete
    result = await delete_location(db_session, chat_id)
    assert result is True
    
    loc = await get_location(db_session, chat_id)
    assert loc is None
    
    # Delete non-existent
    result = await delete_location(db_session, 2222)
    assert result is False

@pytest.mark.asyncio
async def test_save_feedback(db_session):
    from app.repositories.sqlite import SQLiteLocationRepository
    repo = SQLiteLocationRepository(db_session)
    
    chat_id = 12345
    lat = 13.0
    lng = 100.0
    
    feedback = await repo.save_feedback(chat_id, lat, lng, "false_alarm", "Source: Tomorrow.io, max_rain: 1.5 mm/hr")
    
    assert feedback is not None
    assert str(feedback.chat_id) == str(chat_id)
    assert feedback.feedback_type == "false_alarm"
    
    # Check if api_reliability for Tomorrow.io has been updated
    reliabilities = await repo.get_all_api_reliability()
    assert "tomorrow" in reliabilities
    
    # Defaults are 0 queries, 1 false alarm, so accuracy should be 0.0 initially because total < false alarms
    # Let's add a success query first to see real calculation
    await repo.record_api_query_success("tomorrow")
    await repo.record_api_query_success("tomorrow")
    # Now total_queries = 2, false_alarms = 1 => accuracy = 0.5
    
    # another false alarm
    await repo.save_feedback(chat_id, lat, lng, "false_alarm", "Source: Tomorrow.io, max_rain: 1.5 mm/hr")
    
    reliabilities_new = await repo.get_all_api_reliability()
    assert reliabilities_new["tomorrow"] == 0.0  # (2 queries, 2 false alarms) => 0.0

@pytest.mark.asyncio
async def test_schema_migrations_add_missing_columns_idempotently():
    from sqlalchemy import inspect, text
    from app.main import ensure_schema_migrations

    migration_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    try:
        async with migration_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE user_locations (
                        id INTEGER PRIMARY KEY,
                        chat_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL DEFAULT 'default',
                        latitude FLOAT NOT NULL,
                        longitude FLOAT NOT NULL,
                        retention_type VARCHAR NOT NULL
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE TABLE radar_latest_cache (
                        station_code VARCHAR PRIMARY KEY,
                        frames_json TEXT,
                        created_at TIMESTAMP NOT NULL,
                        last_gif_fallback_time FLOAT NOT NULL DEFAULT 0.0
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO user_locations
                        (chat_id, latitude, longitude, retention_type)
                    VALUES
                        ('schema_user', 13.0, 100.0, 'FOREVER')
                    """
                )
            )

            await conn.run_sync(ensure_schema_migrations)
            await conn.run_sync(ensure_schema_migrations)

            def get_cols(sync_conn, table_name):
                return {column["name"] for column in inspect(sync_conn).get_columns(table_name)}

            columns = await conn.run_sync(get_cols, "user_locations")
            assert {
                "last_alert_max_rain",
                "tracking_mode",
                "locked_target_id",
                "locked_target_cx",
                "locked_target_cy",
                "is_snoozed",
                "snooze_until",
                "presence_policy",
                "schedule_active_days",
                "schedule_active_start",
                "schedule_active_end",
                "presence_answer_ttl_minutes",
                "default_fallback_policy",
            }.issubset(columns)

            radar_columns = await conn.run_sync(get_cols, "radar_latest_cache")
            assert "source" in radar_columns

            row = (
                await conn.execute(
                    text(
                        """
                        SELECT
                            is_snoozed,
                            snooze_until,
                            presence_policy,
                            presence_answer_ttl_minutes,
                            default_fallback_policy,
                            tracking_mode
                        FROM user_locations
                        WHERE chat_id = 'schema_user'
                        """
                    )
                )
            ).first()
            assert row == (0, None, "always_ask", 120, "notify", "auto")
    finally:
        await migration_engine.dispose()


@pytest.mark.asyncio
async def test_record_api_query_success(db_session):
    from app.repositories.sqlite import SQLiteLocationRepository
    repo = SQLiteLocationRepository(db_session)
    
    await repo.record_api_query_success("xweather")
    reliabilities = await repo.get_all_api_reliability()
    assert reliabilities["xweather"] == 1.0
    
    # Test fallback defaults
    assert reliabilities["tomorrow"] == 0.95
