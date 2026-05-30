from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import UserLocation
from app.repositories.base import LocationRepository

class SQLiteLocationRepository(LocationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_location(self, chat_id: int) -> Optional[UserLocation]:
        result = await self.session.execute(select(UserLocation).where(UserLocation.chat_id == chat_id))
        return result.scalars().first()

    async def save_location(self, chat_id: int, lat: float, lng: float, retention_type: str) -> UserLocation:
        loc = await self.get_location(chat_id)
        
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
            self.session.add(loc)
            
        await self.session.commit()
        await self.session.refresh(loc)
        return loc

    async def get_active_locations(self) -> List[UserLocation]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await self.session.execute(
            select(UserLocation).where(
                (UserLocation.expires_at == None) | (UserLocation.expires_at > now)
            )
        )
        return list(result.scalars().all())

    async def update_last_alerted(self, location: UserLocation, alerted_time: datetime) -> UserLocation:
        location.last_alerted_at = alerted_time.replace(tzinfo=None)
        await self.session.commit()
        return location

    async def delete_location(self, chat_id: int) -> bool:
        loc = await self.get_location(chat_id)
        if loc:
            await self.session.delete(loc)
            await self.session.commit()
            return True
        return False
