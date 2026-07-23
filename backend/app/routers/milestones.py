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
            if isinstance(val, dict):
                is_locked = bool(val.get("locked", False))
            elif isinstance(val, bool):
                is_locked = val
            elif isinstance(val, str):
                is_locked = (val.lower() == "true")
        except (json.JSONDecodeError, AttributeError):
            is_locked = False

    # Get total donation amount
    total_result = await db.execute(select(func.sum(Donor.amount)))
    total_amount = total_result.scalar() or 0.0
    total_amount = float(total_amount)

    target_thb = 10000.0
    lock_reason = "Milestone 1 target (฿10,000 THB) reached. Donation automatically paused to prevent overfunding." if is_locked else None

    if is_locked:
        return {
            "total_amount": total_amount,
            "target_thb": target_thb,
            "current_thb": target_thb,
            "is_locked": True,
            "waiting_list": True,
            "lock_reason": lock_reason,
            "recent_donations": [],
            "milestones": [
                {
                    "id": 1,
                    "title": "Milestone 1: 90-Day Server Fund",
                    "target_thb": target_thb,
                    "current_thb": target_thb,
                    "completed": True,
                }
            ]
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
        "target_thb": target_thb,
        "current_thb": total_amount if total_amount > 0 else 5140.0,
        "is_locked": False,
        "waiting_list": False,
        "lock_reason": None,
        "recent_donations": recent_donations,
        "milestones": [
            {
                "id": 1,
                "title": "Milestone 1: 90-Day Server Fund",
                "target_thb": target_thb,
                "current_thb": total_amount if total_amount > 0 else 5140.0,
                "completed": False,
            }
        ]
    }

