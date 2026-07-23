from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import json
import sqlite3
import logging
from pathlib import Path
from app.services import transaction_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks", "stripe"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
# Resolve DB path relative to this file: backend/app/routers -> backend/
_MODULE_DIR = Path(__file__).resolve().parent.parent.parent  # -> backend/
DB_PATH = str(_MODULE_DIR / "fonmayang.db")


def _update_balance_in_db(amount_total):
    """Atomically add amount_total (in THB) to system_config total_balance_thb."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS system_config (key VARCHAR PRIMARY KEY, value_json TEXT);")
        cursor.execute("SELECT value_json FROM system_config WHERE key = 'total_balance_thb'")
        row = cursor.fetchone()
        curr = float(json.loads(row[0])) if row else 5140.0
        add_amt = float(amount_total) if amount_total is not None else 0.0
        new_bal = curr + add_amt
        cursor.execute(
            "INSERT INTO system_config (key, value_json) VALUES ('total_balance_thb', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json;",
            (json.dumps(new_bal),)
        )
        conn.commit()
        conn.close()
        logging.info(f"[STRIPE] Updated total_balance_thb: {curr} + {add_amt} = {new_bal}")
    except Exception as e:
        logging.error(f"[STRIPE] Error updating total_balance_thb in DB '{DB_PATH}': {e}")


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # StripeObject in some versions doesn't have .get(); use dict-style access
        def _get(obj, key, default=None):
            try:
                return obj[key]
            except (KeyError, TypeError):
                return getattr(obj, key, default)

        customer_id = _get(session, 'customer')
        transaction_id = _get(session, 'payment_intent') or _get(session, 'subscription')
        amount_total = _get(session, 'amount_total')

        logging.info(f"[STRIPE] checkout.session.completed: customer={customer_id} amount_total={amount_total}")

        # Zero PII: Do not extract names, emails, addresses
        await transaction_service.save_stripe_transaction(
            customer_id=customer_id,
            transaction_id=transaction_id,
            amount=amount_total
        )

        # Update real-time balance in system_config
        _update_balance_in_db(amount_total)

    return {"status": "success"}
