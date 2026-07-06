import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

from app.database import Base
from app.repositories.sqlite import SQLiteLocationRepository
from app.models import AdminBypass

# Setup in-memory SQLite database
@pytest_asyncio.fixture
async def sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def sqlite_session(sqlite_engine):
    async_session = sessionmaker(
        sqlite_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_admin_bypass_sqlite(sqlite_session):
    repo = SQLiteLocationRepository(sqlite_session)
    chat_id = 123456789

    # Initially, no bypass
    has_bypass = await repo.has_active_admin_bypass(chat_id)
    assert has_bypass is False

    # Save bypass (1 hour)
    await repo.save_admin_bypass(chat_id, expires_in_minutes=60)
    has_bypass = await repo.has_active_admin_bypass(chat_id)
    assert has_bypass is True

    # Test expiration (manually edit the record to simulate expiration)
    from sqlalchemy.future import select
    result = await sqlite_session.execute(select(AdminBypass).where(AdminBypass.chat_id == chat_id))
    record = result.scalars().first()
    assert record is not None
    # Expire it manually
    record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    await sqlite_session.commit()
    
    has_bypass = await repo.has_active_admin_bypass(chat_id)
    assert has_bypass is False

    # Save again, then delete
    await repo.save_admin_bypass(chat_id, expires_in_minutes=60)
    assert await repo.has_active_admin_bypass(chat_id) is True

    await repo.delete_admin_bypass(chat_id)
    assert await repo.has_active_admin_bypass(chat_id) is False
