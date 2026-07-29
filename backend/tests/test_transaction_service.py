"""
Unit tests for app.services.transaction_service (Issue #223, #224).

Covers:
  - hash_transaction_id() determinism, uniqueness, output format
  - save_stripe_transaction() Zero-PII persistence, idempotency, invalid input guard

Zero-PII principle: The Donor model must NEVER store email, name, phone or any
customer-identifying information.  These tests assert that explicitly.

No real DB connections are used.  All SQLAlchemy interactions are mocked.
"""
import os
import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# ---------------------------------------------------------------------------
# Ensure a known HASH_SALT is set before importing the module under test.
# Using os.environ.setdefault so we do not overwrite an existing CI value.
# ---------------------------------------------------------------------------
os.environ.setdefault("HASH_SALT", "test_salt_for_unit_tests")


# ---------------------------------------------------------------------------
# Import helpers (done after env is patched)
# ---------------------------------------------------------------------------
from app.services.transaction_service import hash_transaction_id


# ===========================================================================
# Tests for hash_transaction_id()
# ===========================================================================

class TestHashTransactionId:
    """Tests for the hash_transaction_id() helper."""

    def test_hash_is_deterministic_same_salt(self, monkeypatch):
        """Calling with the same tx_id and same HASH_SALT returns the same hash."""
        monkeypatch.setenv("HASH_SALT", "stable_salt")
        result_1 = hash_transaction_id("pi_abc123")
        result_2 = hash_transaction_id("pi_abc123")
        assert result_1 == result_2

    def test_hash_changes_when_salt_changes(self, monkeypatch):
        """Changing HASH_SALT produces a different hash for the same tx_id."""
        monkeypatch.setenv("HASH_SALT", "salt_alpha")
        hash_alpha = hash_transaction_id("pi_abc123")

        monkeypatch.setenv("HASH_SALT", "salt_beta")
        hash_beta = hash_transaction_id("pi_abc123")

        assert hash_alpha != hash_beta

    def test_different_transaction_ids_produce_different_hashes(self, monkeypatch):
        """Two distinct transaction IDs must produce distinct hashes."""
        monkeypatch.setenv("HASH_SALT", "stable_salt")
        hash_a = hash_transaction_id("pi_transaction_A")
        hash_b = hash_transaction_id("pi_transaction_B")
        assert hash_a != hash_b

    def test_output_is_64_char_hex_string(self, monkeypatch):
        """Output must be a 64-character lowercase hex string (SHA-256 digest)."""
        monkeypatch.setenv("HASH_SALT", "stable_salt")
        result = hash_transaction_id("pi_any_id")
        assert isinstance(result, str)
        assert len(result) == 64
        # Verify it is valid hexadecimal
        int(result, 16)  # raises ValueError if not valid hex

    def test_hash_matches_expected_sha256(self, monkeypatch):
        """Manual cross-check: result matches hashlib.sha256(tx_id+salt)."""
        monkeypatch.setenv("HASH_SALT", "verify_salt")
        tx_id = "pi_verify_me"
        expected = hashlib.sha256(f"{tx_id}verify_salt".encode("utf-8")).hexdigest()
        assert hash_transaction_id(tx_id) == expected


# ===========================================================================
# Tests for save_stripe_transaction()
# ===========================================================================

class TestSaveStripeTransaction:
    """Tests for the async save_stripe_transaction() function."""

    def _make_mock_session(self, existing_donor=None):
        """
        Build a mock async context manager that simulates AsyncSessionLocal.

        Parameters
        ----------
        existing_donor: Optional[Donor]
            If provided, the mock DB will return it on scalar_one_or_none(),
            simulating a duplicate record found scenario.
        """
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_donor

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Support `async with AsyncSessionLocal() as db:`
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session_cm)
        return mock_session_factory, mock_session

    # ------------------------------------------------------------------
    # Test: creates Donor with Zero-PII fields only
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_saves_donor_with_hashed_transaction_id(self, monkeypatch):
        """save_stripe_transaction() writes a Donor whose hashed_transaction_id
        is the SHA-256 hash of the raw tx_id — NOT the raw Stripe ID."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session(existing_donor=None)

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            result = await save_stripe_transaction(
                customer_id="cus_test_123",
                transaction_id="pi_real_stripe_id",
                amount=10000,
            )

        assert result is True
        mock_session.add.assert_called_once()
        saved_donor = mock_session.add.call_args[0][0]

        expected_hash = hash_transaction_id("pi_real_stripe_id")
        assert saved_donor.hashed_transaction_id == expected_hash
        # The raw Stripe payment_intent ID must NOT appear in the saved hash
        assert "pi_real_stripe_id" not in saved_donor.hashed_transaction_id

    @pytest.mark.asyncio
    async def test_saves_donor_with_pseudonym_anonymous(self, monkeypatch):
        """Pseudonym field must always be 'Anonymous' (Zero-PII)."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session(existing_donor=None)

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            await save_stripe_transaction(
                customer_id="cus_test_123",
                transaction_id="pi_anon_test",
                amount=5000,
            )

        saved_donor = mock_session.add.call_args[0][0]
        assert saved_donor.pseudonym == "Anonymous"

    @pytest.mark.asyncio
    async def test_amount_converted_from_cents_to_thb(self, monkeypatch):
        """Amount stored in Donor must be amount / 100 (satang → THB)."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session(existing_donor=None)

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            await save_stripe_transaction(
                customer_id="cus_test_123",
                transaction_id="pi_amount_test",
                amount=10000,  # 100 THB in satang
            )

        saved_donor = mock_session.add.call_args[0][0]
        assert saved_donor.amount == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_no_pii_fields_on_donor(self, monkeypatch):
        """Donor model must NOT contain email, name, phone, or customer_id."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session(existing_donor=None)

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            await save_stripe_transaction(
                customer_id="cus_pii_test",
                transaction_id="pi_pii_test",
                amount=2000,
            )

        saved_donor = mock_session.add.call_args[0][0]

        # None of these PII attributes should exist on the Donor model
        pii_attributes = ["email", "name", "phone", "customer_id", "customer_email"]
        for attr in pii_attributes:
            assert not hasattr(saved_donor, attr), (
                f"PII field '{attr}' must NOT be stored on the Donor record"
            )

    # ------------------------------------------------------------------
    # Test: idempotency — duplicate tx_id must not create a second record
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_idempotency_skips_existing_transaction(self, monkeypatch):
        """Calling with the same transaction_id twice must return True but
        NOT call db.add() the second time (idempotent write)."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        # Simulate existing record returned on DB query
        existing_donor = MagicMock()
        mock_factory, mock_session = self._make_mock_session(
            existing_donor=existing_donor
        )

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            result = await save_stripe_transaction(
                customer_id="cus_dup",
                transaction_id="pi_duplicate",
                amount=5000,
            )

        assert result is True
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    # ------------------------------------------------------------------
    # Test: None / empty transaction_id guard
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_false_when_transaction_id_is_none(self, monkeypatch):
        """save_stripe_transaction() with transaction_id=None returns False
        without touching the DB."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session()

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            result = await save_stripe_transaction(
                customer_id="cus_none",
                transaction_id=None,
                amount=5000,
            )

        assert result is False
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_when_transaction_id_is_empty_string(
        self, monkeypatch
    ):
        """save_stripe_transaction() with transaction_id='' returns False
        without touching the DB."""
        monkeypatch.setenv("HASH_SALT", "test_salt_for_unit_tests")

        mock_factory, mock_session = self._make_mock_session()

        with patch("app.services.transaction_service.AsyncSessionLocal", mock_factory):
            from app.services.transaction_service import save_stripe_transaction
            result = await save_stripe_transaction(
                customer_id="cus_empty",
                transaction_id="",
                amount=5000,
            )

        assert result is False
        mock_session.add.assert_not_called()
