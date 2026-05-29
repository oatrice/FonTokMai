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
    assert loc.chat_id == chat_id
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
