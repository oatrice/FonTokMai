from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.database import get_db
from app.models import Donor
import logging

router = APIRouter(prefix="/api/v1/financial", tags=["financial"])

def get_badge(amount: float) -> str:
    if amount > 1000:
        return "Ecosystem Guardian"
    return "Supporter"

@router.get("/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            Donor.token,
            Donor.pseudonym,
            func.sum(Donor.amount).label("total_amount")
        )
        .group_by(Donor.token, Donor.pseudonym)
        .order_by(func.sum(Donor.amount).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    leaderboard = []
    for row in rows:
        leaderboard.append({
            "token": row.token,
            "pseudonym": row.pseudonym or "Anonymous",
            "total_amount": float(row.total_amount),
            "badge": get_badge(float(row.total_amount))
        })
        
    return leaderboard
