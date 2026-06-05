from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import UserLocation
from datetime import datetime, timedelta, timezone
import math

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371.0 # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

async def get_location(session: AsyncSession, chat_id: int, name: str = "default") -> UserLocation:
    result = await session.execute(
        select(UserLocation).where(
            UserLocation.chat_id == chat_id,
            UserLocation.name == name
        )
    )
    return result.scalars().first()

async def save_location(session: AsyncSession, chat_id: int, lat: float, lng: float, retention_type: str, name: str = "default") -> UserLocation:
    loc = await get_location(session, chat_id, name)
    
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
            name=name,
            latitude=lat,
            longitude=lng,
            retention_type=retention_type,
            expires_at=expires_at
        )
        session.add(loc)
        
    await session.commit()
    await session.refresh(loc)
    return loc

async def delete_location(session: AsyncSession, chat_id: int, name: str = "default") -> bool:
    loc = await get_location(session, chat_id, name)
    if loc:
        await session.delete(loc)
        await session.commit()
        return True
    return False

async def get_active_locations(session: AsyncSession) -> list[UserLocation]:
    """Get all locations that are not expired."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await session.execute(
        select(UserLocation).where(
            (UserLocation.expires_at == None) | (UserLocation.expires_at > now)
        )
    )
    return list(result.scalars().all())

async def update_last_alerted_at(session: AsyncSession, chat_id: int) -> bool:
    """Update last_alerted_at to current UTC time."""
    loc = await get_location(session, chat_id)
    if loc:
        loc.last_alerted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()
        return True
    return False
