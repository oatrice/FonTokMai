#!/usr/bin/env python3
"""
Trigger local Stripe payout webhook with valid HMAC signature.
Usage:
    python backend/scripts/trigger_payout_webhook.py created
    python backend/scripts/trigger_payout_webhook.py paid
    python backend/scripts/trigger_payout_webhook.py failed
"""
import sys
import time
import json
import hmac
import hashlib
import urllib.request
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8000/api/webhooks/stripe")
SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret_for_dev_only")

event_type_arg = sys.argv[1] if len(sys.argv) > 1 else "created"

EVENT_MAP = {
    "created": "payout.created",
    "paid": "payout.paid",
    "failed": "payout.failed"
}

event_type = EVENT_MAP.get(event_type_arg, f"payout.{event_type_arg}")

payload_obj = {
    "id": f"evt_test_{int(time.time())}",
    "object": "event",
    "api_version": "2023-10-16",
    "created": int(time.time()),
    "type": event_type,
    "data": {
        "object": {
            "id": "po_test_manual_123",
            "object": "payout",
            "amount": 500000,
            "currency": "thb",
            "status": "pending" if event_type_arg == "created" else ("paid" if event_type_arg == "paid" else "failed"),
            "arrival_date": 1754000000,
            "failure_code": "account_closed" if event_type_arg == "failed" else None,
            "failure_message": "The bank account has been closed." if event_type_arg == "failed" else None
        }
    }
}

payload_bytes = json.dumps(payload_obj).encode("utf-8")
timestamp = int(time.time())
signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes

signature = hmac.new(
    SECRET.encode("utf-8"),
    signed_payload,
    hashlib.sha256
).hexdigest()

sig_header = f"t={timestamp},v1={signature}"

req = urllib.request.Request(
    WEBHOOK_URL,
    data=payload_bytes,
    headers={
        "Content-Type": "application/json",
        "Stripe-Signature": sig_header
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        print(f"Status: {resp.status}")
        print(f"Response: {resp.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
