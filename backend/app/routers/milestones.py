from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import json

from app.database import get_db
from app.models import Donor, SystemConfig

router = APIRouter(prefix="/api", tags=["milestones"])

@router.get("/milestones")
async def get_milestones(db: AsyncSession = Depends(get_db)):
    # Check lock state in SystemConfig
    config_result = await db.execute(select(SystemConfig).where(SystemConfig.key == "milestone_lock"))
    config_record = config_result.scalars().first()
    
    is_locked = False
    if config_record and config_record.value_json:
        try:
            val = json.loads(config_record.value_json)
            is_locked = bool(val.get("locked", False))
        except (json.JSONDecodeError, AttributeError):
            is_locked = False

    # Get total donation amount
    total_result = await db.execute(select(func.sum(Donor.amount)))
    total_amount = total_result.scalar() or 0.0
    total_amount = float(total_amount)

    if is_locked:
        return {
            "total_amount": total_amount,
            "is_locked": True,
            "waiting_list": True,
            "recent_donations": []
        }

    # Fetch recent donations when not locked
    donors_result = await db.execute(
        select(Donor).order_by(Donor.timestamp.desc())
    )
    donors = donors_result.scalars().all()

    recent_donations = [
        {
            "id": donor.id,
            "amount": float(donor.amount),
            "timestamp": donor.timestamp.isoformat() if donor.timestamp else None
        }
        for donor in donors
    ]

    return {
        "total_amount": total_amount,
        "is_locked": False,
        "waiting_list": False,
        "recent_donations": recent_donations
    }
