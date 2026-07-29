# Manual Verification Plan - Stripe Checkout & Neon Postgres Integration

- **Branch**: `feat/223-224-stripe-neon-integration`
- **MR / Issue ID**: `#208, #216, #223, #224`
- **Date**: `2026-07-29`

---

## 📌 Prerequisites & Environment Setup
1. **Environment Variables Needed** (update in `backend/.env`):
   ```env
   STRIPE_SECRET_KEY=sk_test_... (from Stripe Dashboard)
   DATABASE_URL=postgresql+asyncpg://user:password@... (Neon Postgres connection string)
   HASH_SALT=your_secure_salt_string
   FRONTEND_URL=http://localhost:3000
   ```
2. **Launch Development Servers**:
   - Backend:
     ```bash
     cd backend
     source .venv/bin/activate
     poetry run uvicorn app.main:app --reload
     ```
   - Frontend:
     ```bash
     cd frontend
     npm run dev
     ```

---

## 🧪 Verification Scenarios

### Scenario 1: Create Stripe Checkout Session (Happy Path)
- **Goal**: Verify that users can initiate a donation and receive a valid Stripe Checkout URL.
- **Steps**:
  1. Open the Frontend at `http://localhost:3000`.
  2. Click the **"Contribute"** button on the Financial Dashboard.
  3. Select a preset amount (e.g., 100 THB) or enter a custom amount (e.g., 555 THB) in the Donation Modal.
  4. Click **"Donate with Stripe"**.
- **Expected Outcome**:
  - The modal shows a loading state.
  - The backend returns HTTP `200 OK` with a JSON payload: `{"url": "https://checkout.stripe.com/..."}`.
  - The browser automatically redirects to the Stripe Checkout page displaying "Milestone Contribution" with the exact amount selected.

### Scenario 2: Verify Input Validation (Edge Case)
- **Goal**: Ensure the backend rejects invalid donation amounts to prevent abuse.
- **Steps**:
  1. Use cURL to send an invalid amount (e.g., 5 THB, which is below the 10 THB minimum):
     ```bash
     curl -X POST http://localhost:8000/api/v1/donations/create-stripe-session \
          -H "Content-Type: application/json" \
          -d '{"amount_thb": 5}'
     ```
- **Expected Outcome**:
  - HTTP Status: `422 Unprocessable Entity`
  - Response Body: Validation Error detailing "Minimum donation amount is 10 THB".

### Scenario 3: Verify Zero-PII Webhook Persistence (Database & Security)
- **Goal**: Confirm that completed Stripe payments are recorded in Neon Postgres *without* any Personal Identifiable Information (PII).
- **Steps**:
  1. Complete a test payment on the Stripe Checkout page from Scenario 1.
  2. (Alternatively, trigger the webhook via Stripe CLI if set up, or wait for the webhook payload).
  3. Inspect the Neon Postgres `donors` table.
     ```sql
     SELECT * FROM donors ORDER BY timestamp DESC LIMIT 1;
     ```
- **Expected Outcome**:
  - The record is created successfully.
  - `hashed_transaction_id` contains a 64-character SHA-256 hash (NOT the raw `cs_test_...` ID).
  - `pseudonym` is strictly `"Anonymous"`.
  - `amount` correctly matches the THB amount.
  - There are **no columns or data** containing the user's real name, email, or phone number.

### Scenario 4: Webhook Idempotency (Edge Case)
- **Goal**: Ensure duplicate webhooks do not result in double-counting donations.
- **Steps**:
  1. Re-send the exact same webhook payload to the backend.
- **Expected Outcome**:
  - HTTP Status: `200 OK` (webhook acknowledged).
  - Database: No new record is created in the `donors` table (the row count remains unchanged).
  - Logs show: `"Transaction <hash> already exists. Skipping."`

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `pytest` result: `24 passed, 0 failed` (including unit tests for Zero-PII logic, validation, and env sync).
- **Test Output Snippet**:
  ```text
  backend/tests/test_transaction_service.py::TestSaveStripeTransaction::test_no_pii_fields_on_donor PASSED [ 37%]
  backend/tests/test_donations_endpoint.py::TestCreateStripeSession::test_minimum_amount_10_thb_passes_validation PASSED [ 66%]
  ```
