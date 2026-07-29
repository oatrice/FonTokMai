import os
import logging
import hashlib
from datetime import datetime, timezone
import random
import string
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import Donor

def generate_token(length=8):
    characters = string.ascii_letters + string.digits
    return "Fon-" + "".join(random.choice(characters) for _ in range(length))

def hash_transaction_id(tx_id: str) -> str:
    salt = os.getenv("HASH_SALT", "default_dev_salt")
    return hashlib.sha256(f"{tx_id}{salt}".encode('utf-8')).hexdigest()

async def save_stripe_transaction(customer_id: str, transaction_id: str, amount: int):
    logging.info(f"Saving zero-PII transaction: {transaction_id} for amount {amount}")
    
    if not transaction_id:
        logging.warning("No transaction_id provided, skipping DB save.")
        return False
        
    hashed_tx_id = hash_transaction_id(transaction_id)
    token = generate_token()
    
    # Amount from Stripe is usually in cents for some currencies, but for THB it's also in smallest currency unit (satang), so divide by 100
    # Wait, the amount passed from webhook is amount_total which is in cents/satang. We convert to standard unit (THB).
    amount_thb = amount / 100.0 if amount else 0.0

    async with AsyncSessionLocal() as db:
        # Check if already exists to ensure idempotency
        stmt = select(Donor).where(Donor.hashed_transaction_id == hashed_tx_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            logging.info(f"Transaction {hashed_tx_id} already exists. Skipping.")
            return True
            
        new_donor = Donor(
            token=token,
            hashed_transaction_id=hashed_tx_id,
            pseudonym="Anonymous",
            amount=amount_thb,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(new_donor)
        try:
            await db.commit()
            logging.info(f"Successfully saved Donor record with token {token}")
            return True
        except Exception as e:
            await db.rollback()
            logging.error(f"Failed to save donor to DB: {e}")
            return False
