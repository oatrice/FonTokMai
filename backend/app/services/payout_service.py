"""
PayoutService — Business logic for Stripe Auto Payout lifecycle (Issue #210).

Handles payout.created, payout.paid, payout.failed webhook events with strict
idempotency to prevent double-processing on Stripe webhook retries.

Zero-PII: stores only Stripe-generated IDs (po_xxx), no bank account details.
"""
import logging
import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.models import Payout

logger = logging.getLogger(__name__)


class PayoutService:
    def __init__(self, db: Session):
        self.db = db

    # ─── Internal Helpers ────────────────────────────────────────────────────

    def _build_idempotency_key(self, payout_id: str, event_type: str) -> str:
        """Build deterministic idempotency key: {payout_id}-{event_type}"""
        return f"{payout_id}-{event_type}"

    def _find_payout(self, payout_id: str) -> Payout | None:
        """Lookup existing Payout record by Stripe payout_id."""
        return (
            self.db.query(Payout)
            .filter(Payout.payout_id == payout_id)
            .first()
        )

    # ─── Event Handlers ──────────────────────────────────────────────────────

    def handle_payout_created(self, payout_data: Dict[str, Any]) -> Dict:
        """Handle payout.created Stripe event.

        Creates a new Payout audit record. Silently skips if the same
        payout_id has already been processed (idempotency).
        """
        payout_id = payout_data["id"]
        idem_key = self._build_idempotency_key(payout_id, "created")

        existing = self._find_payout(payout_id)
        if existing:
            logger.info(f"[PAYOUT] Duplicate payout.created for {payout_id} — skipping.")
            return {"skipped": True}

        arrival_ts = payout_data.get("arrival_date")
        arrival_dt = (
            datetime.datetime.fromtimestamp(arrival_ts, tz=datetime.timezone.utc)
            if arrival_ts
            else None
        )
        now = datetime.datetime.now(datetime.timezone.utc)

        payout = Payout(
            payout_id=payout_id,
            status="pending",
            amount_cents=int(payout_data.get("amount", 0)),
            currency=payout_data.get("currency", "thb"),
            arrival_date=arrival_dt,
            idempotency_key=idem_key,
            created_at=now,
            updated_at=now,
        )
        self.db.add(payout)
        self.db.commit()
        logger.info(f"[PAYOUT] Recorded payout.created: {payout_id} amount={payout.amount_cents}")
        return {"status": "created"}

    def handle_payout_paid(self, payout_data: Dict[str, Any]) -> Dict:
        """Handle payout.paid Stripe event.

        Updates existing Payout status to 'paid'. Skips gracefully if the
        payout_id is not found in the system.
        """
        payout_id = payout_data["id"]
        payout = self._find_payout(payout_id)

        if not payout:
            logger.warning(f"[PAYOUT] payout.paid received for unknown payout {payout_id} — skipping.")
            return {"skipped": True}

        payout.status = "paid"
        payout.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        logger.info(f"[PAYOUT] Updated status to paid: {payout_id}")
        return {"status": "paid"}

    def handle_payout_failed(self, payout_data: Dict[str, Any]) -> Dict:
        """Handle payout.failed Stripe event.

        Updates existing Payout status to 'failed' and captures
        failure_code + failure_message for audit and alerting.
        """
        payout_id = payout_data["id"]
        payout = self._find_payout(payout_id)

        if not payout:
            logger.warning(f"[PAYOUT] payout.failed received for unknown payout {payout_id} — skipping.")
            return {"skipped": True}

        payout.status = "failed"
        payout.failure_code = payout_data.get("failure_code")
        payout.failure_message = payout_data.get("failure_message")
        payout.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.db.commit()
        logger.error(
            f"[PAYOUT] Payout failed: {payout_id} "
            f"code={payout.failure_code} msg={payout.failure_message}"
        )
        return {"status": "failed"}
