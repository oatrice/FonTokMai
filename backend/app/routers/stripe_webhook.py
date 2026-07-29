from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import json
import sqlite3
import logging
from pathlib import Path
from app.services import transaction_service
from app.services.payout_service import PayoutService
from app.database import AsyncSessionLocal

from sqlalchemy.future import select
from app.models import SystemConfig

router = APIRouter(prefix="/api/webhooks", tags=["webhooks", "stripe"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")


async def _update_balance_in_db(amount_total):
    """Atomically add amount_total (in THB) to system_config total_balance_thb."""
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(SystemConfig).where(SystemConfig.key == 'total_balance_thb')
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()
            
            curr = float(json.loads(config.value_json)) if config else 5140.0
            add_amt = float(amount_total) if amount_total is not None else 0.0
            new_bal = curr + add_amt
            
            if config:
                config.value_json = json.dumps(new_bal)
            else:
                config = SystemConfig(key='total_balance_thb', value_json=json.dumps(new_bal))
                db.add(config)
            
            await db.commit()
            logging.info(f"[STRIPE] Updated total_balance_thb: {curr} + {add_amt} = {new_bal}")
    except Exception as e:
        logging.error(f"[STRIPE] Error updating total_balance_thb in DB: {e}")


@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        if os.getenv("ENVIRONMENT") == "development":
            try:
                logging.warning(f"[STRIPE] Webhook signature verification bypassed in dev mode: {e}")
                event = json.loads(payload.decode('utf-8'))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid payload JSON")
        else:
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
        transaction_id = _get(session, 'payment_intent') or _get(session, 'subscription') or _get(session, 'id')
        amount_total = _get(session, 'amount_total')

        logging.info(f"[STRIPE] checkout.session.completed: customer={customer_id} amount_total={amount_total}")

        # Zero PII: Do not extract names, emails, addresses
        await transaction_service.save_stripe_transaction(
            customer_id=customer_id,
            transaction_id=transaction_id,
            amount=amount_total
        )

        # Update real-time balance in system_config
        await _update_balance_in_db(amount_total)

    elif event['type'] in ('payout.created', 'payout.paid', 'payout.failed'):
        payout_obj = event['data']['object']
        
        # Safely convert StripeObject or dict to standard Python dict
        def _to_dict(obj):
            if isinstance(obj, dict):
                return obj
            res = {}
            for k in ['id', 'amount', 'currency', 'arrival_date', 'status', 'failure_code', 'failure_message']:
                try:
                    res[k] = obj[k]
                except (KeyError, TypeError, AttributeError):
                    pass
            return res

        payout_dict = _to_dict(payout_obj)
        payout_id = payout_dict.get('id', 'unknown')

        async with AsyncSessionLocal() as db:
            svc = PayoutService(db=db)
            if event['type'] == 'payout.created':
                await svc.handle_payout_created(payout_dict)
            elif event['type'] == 'payout.paid':
                await svc.handle_payout_paid(payout_dict)
            elif event['type'] == 'payout.failed':
                await svc.handle_payout_failed(payout_dict)

        logging.info(f"[STRIPE] Handled {event['type']} for payout {payout_id}")

    return {"status": "success"}
