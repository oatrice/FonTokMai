# Manual Verification: Stripe Checkout & Neon Postgres Integration

## Prerequisites
1. Valid `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in `backend/.env`.
2. Valid `DATABASE_URL` pointing to a Neon Postgres database.
3. Stripe CLI installed and authenticated.

## Test Cases

### 1. Zero-PII Donation Flow (Happy Path)
1. Start backend `uvicorn app.main:app --reload`.
2. Start frontend `npm run dev`.
3. Start Stripe webhook forwarding:
   `stripe listen --forward-to localhost:8000/api/webhooks/stripe --api-key <YOUR_TEST_API_KEY>`
4. Go to Frontend UI at `http://localhost:3000`.
5. Click "Donate", select an amount (e.g. 100 THB), and proceed to Stripe Checkout.
6. Enter test card details in Stripe Sandbox and click "Complete test payment".
7. Verify in terminal that `stripe listen` prints `--> checkout.session.completed [evt_...]`.
8. Verify in backend logs that the webhook was received (HTTP 200 OK).
9. Check the database `donors` table (e.g. via Neon console or curl/CLI).
   - Expected: A new row exists with `amount = 100` and `pseudonym = "Anonymous"`.
   - Expected: The `hashed_transaction_id` is a 64-character SHA-256 hash.
   - Expected: No email, name, or phone number is stored (Zero-PII).

### 2. Idempotency Check
1. In the terminal, manually trigger the same event again using Stripe CLI:
   `stripe trigger checkout.session.completed --api-key <YOUR_TEST_API_KEY>`
2. Verify the backend returns 200 OK.
3. Check the database `donors` table.
   - Expected: The number of rows for that hash should not increase (duplicate event ignored).

### 3. Missing Signature (Dev Mode bypass)
1. Send a mock request without Stripe headers:
   `curl -X POST http://localhost:8000/api/webhooks/stripe -H "mock_dev_sig: true" -d '{"type": "checkout.session.completed", "data": {"object": {"id": "cs_test_mock", "amount_total": 5000, "currency": "thb"}}}'`
2. Verify backend returns 200 OK and handles the event (creates row if valid).
