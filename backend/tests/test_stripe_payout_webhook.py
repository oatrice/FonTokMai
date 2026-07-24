"""
Tests for Stripe Payout Webhook handlers (Issue #210).

Tests use strict TDD: RED → GREEN → REFACTOR.
Each test covers ONE behavior only.
"""
import pytest
import datetime
import stripe
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app

client = TestClient(app)


# ─── Existing Tests (kept for regression) ─────────────────────────────────────

def test_stripe_webhook_invalid_signature():
    response = client.post(
        "/api/webhooks/stripe",
        json={"type": "checkout.session.completed"},
        headers={"Stripe-Signature": "invalid_signature"},
    )
    assert response.status_code == 400
    assert (
        "Invalid signature" in response.text
        or "Signature verification failed" in response.text
        or "Webhook Error" in response.text
    )


def test_stripe_webhook_valid_payload_saves_zero_pii(mocker):
    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=stripe.Event.construct_from(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer": "cus_12345",
                        "payment_intent": "pi_12345",
                        "amount_total": 5000,
                        "customer_email": "test@example.com",
                        "customer_details": {"name": "Test User"},
                    }
                },
            },
            stripe.api_key,
        ),
    )
    mock_save = mocker.patch(
        "app.routers.stripe_webhook.transaction_service.save_stripe_transaction"
    )
    response = client.post(
        "/api/webhooks/stripe",
        data="raw_payload_data",
        headers={"Stripe-Signature": "valid_signature"},
    )
    assert response.status_code == 200
    mock_save.assert_called_once_with(
        customer_id="cus_12345",
        transaction_id="pi_12345",
        amount=5000,
    )


# ─── Task 1: Payout Model ──────────────────────────────────────────────────────

def test_payout_model_exists():
    """Payout model ต้องมีอยู่ใน SQLAlchemy metadata"""
    from app.models import Base, Payout  # noqa: F401

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    assert "payouts" in Base.metadata.tables


def test_payout_model_has_required_columns():
    """Payout table ต้องมี columns ที่ครบถ้วนตาม spec"""
    from app.models import Payout

    payout_cols = {c.name for c in Payout.__table__.columns}
    required = {
        "id",
        "payout_id",
        "status",
        "amount_cents",
        "currency",
        "arrival_date",
        "idempotency_key",
        "failure_code",
        "failure_message",
        "created_at",
        "updated_at",
    }
    assert required.issubset(payout_cols), f"Missing columns: {required - payout_cols}"


def test_payout_idempotency_key_is_unique():
    """idempotency_key column ต้องมี unique constraint"""
    from app.models import Payout

    idem_col = Payout.__table__.columns["idempotency_key"]
    assert idem_col.unique is True, "idempotency_key must have unique=True"


# ─── Task 2: PayoutService ────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Fake SQLAlchemy session ที่ไม่แตะ DB จริง"""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def test_payout_service_saves_created_event(mock_db):
    """payout.created ต้องบันทึก Payout record ใหม่ใน DB"""
    from app.services.payout_service import PayoutService

    svc = PayoutService(db=mock_db)
    result = svc.handle_payout_created({
        "id": "po_test123",
        "status": "pending",
        "amount": 500000,
        "currency": "thb",
        "arrival_date": 1754000000,
    })

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result.get("status") == "created"


def test_payout_service_idempotency_prevents_duplicate(mock_db):
    """ถ้า payout_id ซ้ำ ต้องไม่ add อีกครั้ง (idempotency)"""
    from app.models import Payout
    from app.services.payout_service import PayoutService

    existing = Payout(payout_id="po_dup123", idempotency_key="po_dup123-created")
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    svc = PayoutService(db=mock_db)
    result = svc.handle_payout_created({"id": "po_dup123", "amount": 100, "currency": "thb"})

    mock_db.add.assert_not_called()
    assert result.get("skipped") is True


def test_payout_service_updates_status_on_paid(mock_db):
    """payout.paid ต้อง update status ของ record เดิมเป็น 'paid'"""
    from app.models import Payout
    from app.services.payout_service import PayoutService

    now = datetime.datetime.utcnow()
    existing = Payout(
        payout_id="po_paid123",
        status="pending",
        idempotency_key="po_paid123-created",
        amount_cents=500000,
        currency="thb",
        created_at=now,
        updated_at=now,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    svc = PayoutService(db=mock_db)
    svc.handle_payout_paid({"id": "po_paid123"})

    assert existing.status == "paid"
    mock_db.commit.assert_called_once()


def test_payout_service_captures_failure_reason(mock_db):
    """payout.failed ต้องบันทึก failure_code และ failure_message"""
    from app.models import Payout
    from app.services.payout_service import PayoutService

    now = datetime.datetime.utcnow()
    existing = Payout(
        payout_id="po_fail456",
        status="pending",
        idempotency_key="po_fail456-created",
        amount_cents=100000,
        currency="thb",
        created_at=now,
        updated_at=now,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = existing

    svc = PayoutService(db=mock_db)
    svc.handle_payout_failed({
        "id": "po_fail456",
        "failure_code": "insufficient_funds",
        "failure_message": "Your Stripe account has insufficient funds.",
    })

    assert existing.status == "failed"
    assert existing.failure_code == "insufficient_funds"
    assert "insufficient funds" in existing.failure_message
    mock_db.commit.assert_called_once()


def test_payout_service_unknown_payout_paid_skips(mock_db):
    """payout.paid สำหรับ payout_id ที่ไม่รู้จัก ต้อง skip ไม่ crash"""
    from app.services.payout_service import PayoutService

    # DB returns None — payout ไม่อยู่ใน system
    mock_db.query.return_value.filter.return_value.first.return_value = None

    svc = PayoutService(db=mock_db)
    result = svc.handle_payout_paid({"id": "po_unknown"})

    mock_db.commit.assert_not_called()
    assert result.get("skipped") is True


# ─── Task 3: Webhook Routing ──────────────────────────────────────────────────

def _build_stripe_event(event_type: str, obj: dict):
    return stripe.Event.construct_from(
        {"type": event_type, "data": {"object": obj}},
        stripe.api_key,
    )


def test_stripe_webhook_handles_payout_created(mocker):
    """POST /api/webhooks/stripe ต้อง route payout.created ไปยัง PayoutService"""
    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=_build_stripe_event(
            "payout.created",
            {"id": "po_wh_test", "amount": 500000, "currency": "thb", "arrival_date": 1754000000},
        ),
    )
    mock_handle = mocker.patch(
        "app.routers.stripe_webhook.PayoutService.handle_payout_created",
        return_value={"status": "created"},
    )
    response = client.post(
        "/api/webhooks/stripe", data="payload", headers={"Stripe-Signature": "valid"}
    )
    assert response.status_code == 200
    mock_handle.assert_called_once()


def test_stripe_webhook_handles_payout_paid(mocker):
    """POST /api/webhooks/stripe ต้อง route payout.paid"""
    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=_build_stripe_event("payout.paid", {"id": "po_paid_wh"}),
    )
    mock_handle = mocker.patch(
        "app.routers.stripe_webhook.PayoutService.handle_payout_paid",
        return_value={"status": "paid"},
    )
    response = client.post(
        "/api/webhooks/stripe", data="payload", headers={"Stripe-Signature": "valid"}
    )
    assert response.status_code == 200
    mock_handle.assert_called_once()


def test_stripe_webhook_handles_payout_failed(mocker):
    """POST /api/webhooks/stripe ต้อง route payout.failed"""
    mocker.patch(
        "stripe.Webhook.construct_event",
        return_value=_build_stripe_event(
            "payout.failed",
            {"id": "po_fail_wh", "failure_code": "account_closed", "failure_message": "Bank closed."},
        ),
    )
    mock_handle = mocker.patch(
        "app.routers.stripe_webhook.PayoutService.handle_payout_failed",
        return_value={"status": "failed"},
    )
    response = client.post(
        "/api/webhooks/stripe", data="payload", headers={"Stripe-Signature": "valid"}
    )
    assert response.status_code == 200
    mock_handle.assert_called_once()
