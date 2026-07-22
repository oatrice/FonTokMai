from fastapi import APIRouter, Request, Header, HTTPException
import stripe
import os
import logging
from app.services import transaction_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks", "stripe"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        customer_id = getattr(session, 'customer', None)
        transaction_id = getattr(session, 'payment_intent', None) or getattr(session, 'subscription', None)
        amount_total = getattr(session, 'amount_total', None)
        
        # Zero PII: Do not extract names, emails, addresses
        await transaction_service.save_stripe_transaction(
            customer_id=customer_id,
            transaction_id=transaction_id,
            amount=amount_total
        )
        
    return {"status": "success"}
