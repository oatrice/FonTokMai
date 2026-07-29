"""
Unit tests for POST /api/v1/donations/create-stripe-session (Issue #223, #224).

Covers:
  - Happy-path session creation returning {"url": "..."}.
  - Low-amount payload (validation is client-side; backend accepts any positive int).
  - Missing STRIPE_SECRET_KEY → HTTP 500.
  - Stripe raises an exception → HTTP 500.

No real Stripe API calls are made.  stripe.checkout.Session.create is fully mocked.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# We need STRIPE_SECRET_KEY set before importing main so the app can start.
# Monkeypatching per-test handles per-test overrides.
# ---------------------------------------------------------------------------
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_unit_placeholder")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_stripe_session(url: str = "https://checkout.stripe.com/pay/cs_test_abc123"):
    """Return a MagicMock that behaves like a stripe.checkout.Session object."""
    mock_session = MagicMock()
    mock_session.url = url
    return mock_session


# ===========================================================================
# Tests for POST /api/v1/donations/create-stripe-session
# ===========================================================================

class TestCreateStripeSession:

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_valid_amount_returns_checkout_url(self, monkeypatch):
        """POST with a valid amount (100 THB) returns {"url": "<stripe url>"}."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")
        expected_url = "https://checkout.stripe.com/pay/cs_test_happy"

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(url=expected_url),
        ):
            response = client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 100},
            )

        assert response.status_code == 200
        body = response.json()
        assert "url" in body
        assert body["url"] == expected_url

    def test_response_contains_only_url_key(self, monkeypatch):
        """The response JSON should contain the 'url' key (no PII in response)."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(),
        ):
            response = client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 250},
            )

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"url"}

    # ------------------------------------------------------------------
    # Low-amount (validation is client-side)
    # ------------------------------------------------------------------

    def test_amount_below_minimum_returns_422(self, monkeypatch):
        """The backend enforces a minimum of 10 THB via field_validator.
        Amounts below 10 THB must be rejected with HTTP 422."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        response = client.post(
            "/api/v1/donations/create-stripe-session",
            json={"amount_thb": 1},
        )

        assert response.status_code == 422

    def test_minimum_amount_10_thb_passes_validation(self, monkeypatch):
        """Exactly 10 THB (the minimum) must succeed (HTTP 200)."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")
        expected_url = "https://checkout.stripe.com/pay/cs_test_min_amount"

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(url=expected_url),
        ):
            response = client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 10},
            )

        assert response.status_code == 200
        assert response.json()["url"] == expected_url

    def test_stripe_called_with_correct_amount_in_satang(self, monkeypatch):
        """Stripe should receive amount_thb * 100 as unit_amount (THB → satang)."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(),
        ) as mock_create:
            client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 150},
            )

        call_kwargs = mock_create.call_args[1]  # keyword arguments
        # line_items[0].price_data.unit_amount must be 150 * 100 = 15000
        unit_amount = call_kwargs["line_items"][0]["price_data"]["unit_amount"]
        assert unit_amount == 15000

    def test_stripe_called_with_thb_currency(self, monkeypatch):
        """Stripe checkout session must use THB as currency."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(),
        ) as mock_create:
            client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 100},
            )

        call_kwargs = mock_create.call_args[1]
        currency = call_kwargs["line_items"][0]["price_data"]["currency"]
        assert currency == "thb"

    # ------------------------------------------------------------------
    # Missing STRIPE_SECRET_KEY → HTTP 500
    # ------------------------------------------------------------------

    def test_missing_stripe_key_returns_500(self, monkeypatch):
        """When STRIPE_SECRET_KEY is not configured, the endpoint must return HTTP 500."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "")  # empty = not configured

        response = client.post(
            "/api/v1/donations/create-stripe-session",
            json={"amount_thb": 100},
        )

        assert response.status_code == 500
        body = response.json()
        assert "detail" in body
        assert "Stripe API key" in body["detail"] or "not configured" in body["detail"]

    # ------------------------------------------------------------------
    # Stripe raises an exception → HTTP 500
    # ------------------------------------------------------------------

    def test_stripe_exception_returns_500(self, monkeypatch):
        """When stripe.checkout.Session.create() raises, the endpoint returns HTTP 500."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            side_effect=Exception("Stripe network error"),
        ):
            response = client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 100},
            )

        assert response.status_code == 500
        body = response.json()
        assert "detail" in body

    def test_stripe_api_error_returns_502(self, monkeypatch):
        """When Stripe raises a StripeError (e.g. AuthenticationError),
        the endpoint returns HTTP 502 (payment gateway error), not 500."""
        import stripe as stripe_lib

        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            side_effect=stripe_lib.error.AuthenticationError("No such API key"),
        ):
            response = client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 100},
            )

        assert response.status_code == 502
        body = response.json()
        assert "detail" in body

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def test_missing_amount_field_returns_422(self, monkeypatch):
        """Sending a request body without amount_thb should return HTTP 422."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        response = client.post(
            "/api/v1/donations/create-stripe-session",
            json={},
        )

        assert response.status_code == 422

    def test_optional_client_reference_id_is_forwarded(self, monkeypatch):
        """When client_reference_id is provided, it is passed to Stripe."""
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_valid_key")

        with patch(
            "app.routers.donations.stripe.checkout.Session.create",
            return_value=_mock_stripe_session(),
        ) as mock_create:
            client.post(
                "/api/v1/donations/create-stripe-session",
                json={"amount_thb": 100, "client_reference_id": "user_ref_42"},
            )

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("client_reference_id") == "user_ref_42"
