import os
import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/donations", tags=["Donations"])

class CheckoutSessionRequest(BaseModel):
    amount_thb: int
    client_reference_id: str | None = None

@router.post("/create-stripe-session")
async def create_stripe_session(request: CheckoutSessionRequest):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe API key is not configured")
        
    try:
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "thb",
                    "product_data": {
                        "name": "Milestone Contribution",
                    },
                    "unit_amount": request.amount_thb * 100, # Amount in cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/?payment=success",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/?payment=cancelled",
            client_reference_id=request.client_reference_id,
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
