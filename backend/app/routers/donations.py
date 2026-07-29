import os
import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
import logging

router = APIRouter(prefix="/api/v1/donations", tags=["Donations"])

class CheckoutSessionRequest(BaseModel):
    amount_thb: int
    client_reference_id: str | None = None

    @field_validator("amount_thb")
    @classmethod
    def amount_must_be_positive(cls, v: int) -> int:
        if v < 10:
            raise ValueError("Minimum donation amount is 10 THB")
        if v > 1_000_000:
            raise ValueError("Maximum donation amount is 1,000,000 THB")
        return v

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
                    "unit_amount": request.amount_thb * 100,  # Stripe expects satang (THB cents)
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/?payment=success",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/?payment=cancelled",
            client_reference_id=request.client_reference_id,
        )
        return {"url": session.url}
    except stripe.error.StripeError as e:
        logging.error(f"[STRIPE] Checkout session creation failed: {e}")
        raise HTTPException(status_code=502, detail="Payment gateway error. Please try again.")
    except Exception as e:
        logging.error(f"[DONATIONS] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
