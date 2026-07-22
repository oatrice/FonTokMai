import pytest
from fastapi.testclient import TestClient
from app.main import app
import stripe

client = TestClient(app)

def test_stripe_webhook_invalid_signature():
    response = client.post(
        "/api/webhooks/stripe",
        json={"type": "checkout.session.completed"},
        headers={"Stripe-Signature": "invalid_signature"}
    )
    assert response.status_code == 400
    assert "Invalid signature" in response.text or "Signature verification failed" in response.text or "Webhook Error" in response.text

def test_stripe_webhook_valid_payload_saves_zero_pii(mocker):
    # Mock signature validation to pass
    mocker.patch("stripe.Webhook.construct_event", return_value=stripe.Event.construct_from({
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_12345",
                "payment_intent": "pi_12345",
                "amount_total": 5000,
                "customer_email": "test@example.com",  # Should not be saved
                "customer_details": {"name": "Test User"} # Should not be saved
            }
        }
    }, stripe.api_key))

    # Mock the database/service save call
    # We will implement this in a service
    mock_save = mocker.patch("app.routers.stripe_webhook.transaction_service.save_stripe_transaction")

    response = client.post(
        "/api/webhooks/stripe",
        data="raw_payload_data",
        headers={"Stripe-Signature": "valid_signature"}
    )
    
    assert response.status_code == 200
    # Ensure only zero PII fields are passed to the service
    mock_save.assert_called_once_with(
        customer_id="cus_12345",
        transaction_id="pi_12345",
        amount=5000
    )
