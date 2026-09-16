from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import UserLocation
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/locations", tags=["locations"])

class LocationResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    presence_policy: str
    presence_answer_ttl_minutes: int
    is_snoozed: bool
    snooze_until: Optional[str] = None

@router.get("", response_model=List[LocationResponse])
async def get_locations():
    """Returns all registered user locations for admin configuration and monitoring."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserLocation).order_by(UserLocation.id.asc())
        )
        locations = result.scalars().all()
        return [
            LocationResponse(
                id=loc.id,
                name=loc.name,
                latitude=loc.latitude,
                longitude=loc.longitude,
                presence_policy=getattr(loc, "presence_policy", "always_ask") or "always_ask",
                presence_answer_ttl_minutes=getattr(loc, "presence_answer_ttl_minutes", 120) or 120,
                is_snoozed=bool(loc.is_snoozed_state if hasattr(loc, "is_snoozed_state") else loc.is_snoozed),
                snooze_until=loc.snooze_until.isoformat() if loc.snooze_until else None,
            )
            for loc in locations
        ]
