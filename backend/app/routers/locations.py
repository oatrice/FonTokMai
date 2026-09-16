import os
import secrets
import logging
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import UserLocation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/locations", tags=["locations"])

class LocationResponse(BaseModel):
    id: int
    chat_id: str
    platform: str = "telegram"
    name: str
    latitude: float
    longitude: float
    presence_policy: str
    presence_answer_ttl_minutes: int
    is_snoozed: bool
    snooze_until: Optional[str] = None

def verify_admin_secret(x_cron_secret: Optional[str] = Header(None)) -> bool:
    """Validate admin authorization via CRON_SECRET header to protect location coordinates and chat IDs."""
    server_secret = os.getenv("CRON_SECRET")
    if not server_secret or not x_cron_secret or not secrets.compare_digest(x_cron_secret, server_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@router.get("", response_model=List[LocationResponse])
async def get_locations(_: bool = Depends(verify_admin_secret)):
    """Returns all registered user locations for admin configuration and monitoring."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserLocation).order_by(UserLocation.id.asc())
        )
        locations = result.scalars().all()
        return [
            LocationResponse(
                id=loc.id,
                chat_id=loc.chat_id,
                platform=loc.platform or "telegram",
                name=loc.name,
                latitude=loc.latitude,
                longitude=loc.longitude,
                presence_policy=loc.presence_policy or "always_ask",
                presence_answer_ttl_minutes=loc.presence_answer_ttl_minutes or 120,
                is_snoozed=bool(loc.is_snoozed_state if hasattr(loc, "is_snoozed_state") else loc.is_snoozed),
                snooze_until=loc.snooze_until.isoformat() if loc.snooze_until else None,
            )
            for loc in locations
        ]

