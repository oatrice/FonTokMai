from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import UserLocation
from datetime import datetime, timedelta, timezone

async def get_location(session: AsyncSession, chat_id: int) -> UserLocation:
    result = await session.execute(select(UserLocation).where(UserLocation.chat_id == chat_id))
    return result.scalars().first()

async def save_location(session: AsyncSession, chat_id: int, lat: float, lng: float, retention_type: str) -> UserLocation:
    loc = await get_location(session, chat_id)
    
    expires_at = None
    if retention_type == "TWO_MONTHS":
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=60)
        
    if loc:
        loc.latitude = lat
        loc.longitude = lng
        loc.retention_type = retention_type
        loc.expires_at = expires_at
    else:
        loc = UserLocation(
            chat_id=chat_id,
            latitude=lat,
            longitude=lng,
            retention_type=retention_type,
            expires_at=expires_at
        )
        session.add(loc)
        
    await session.commit()
    await session.refresh(loc)
    return loc

async def delete_location(session: AsyncSession, chat_id: int) -> bool:
    loc = await get_location(session, chat_id)
    if loc:
        await session.delete(loc)
        await session.commit()
        return True
    return False
