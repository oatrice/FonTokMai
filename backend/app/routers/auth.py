from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from app.database import get_db
from app.models import Donor
from app.services.event_broadcaster import EventBroadcaster
import secrets
import string
import datetime
import bcrypt

router = APIRouter(prefix="/auth", tags=["auth"])

class DonationSuccessReq(BaseModel):
    transaction_id: str
    amount: float
    timestamp: datetime.datetime

class RecoveryReq(BaseModel):
    transaction_id: str
    amount: float
    timestamp: datetime.datetime

def hash_transaction(tx_id: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(tx_id.encode('utf-8'), salt).decode('utf-8')

def check_transaction(tx_id: str, hashed: str) -> bool:
    return bcrypt.checkpw(tx_id.encode('utf-8'), hashed.encode('utf-8'))

def generate_magic_token() -> str:
    # Format: Fon-XXXX-XXXX
    part1 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    part2 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    return f"Fon-{part1}-{part2}"

@router.post("/generate-token")
async def generate_token(req: DonationSuccessReq, db: AsyncSession = Depends(get_db)):
    token = generate_magic_token()
    hashed_tx = hash_transaction(req.transaction_id)
    
    new_donor = Donor(
        token=token,
        hashed_transaction_id=hashed_tx,
        amount=req.amount,
        timestamp=req.timestamp
    )
    db.add(new_donor)
    await db.commit()
    await db.refresh(new_donor)
    
    try:
        broadcaster = EventBroadcaster()
        await broadcaster.broadcast_event('new_donation', {'token': token, 'amount': req.amount})
    except Exception as e:
        pass

    
    return {"token": token}

@router.post("/recover")
async def recover_account(req: RecoveryReq, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Donor).where(Donor.amount == req.amount))
    donors = result.scalars().all()
    
    for donor in donors:
        # DB may strip tzinfo or truncate microseconds. 
        # Convert both to naive and compare with 1 second tolerance
        dt1 = donor.timestamp.replace(tzinfo=None)
        dt2 = req.timestamp.replace(tzinfo=None)
        
        if abs((dt1 - dt2).total_seconds()) < 1:
            if check_transaction(req.transaction_id, donor.hashed_transaction_id):
                return {"token": donor.token, "message": "Recovery successful"}
                
    raise HTTPException(status_code=401, detail="Invalid recovery credentials")
