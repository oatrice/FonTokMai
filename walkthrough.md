# QA Walkthrough

## Walkthrough: MR 2 - Zero-PII Stripe Webhook Listener
- **Objective**: Implement a secure Stripe webhook listener that processes payment and subscription events while storing zero PII (Personally Identifiable Information).
- **Changes Made**:
  1. **Added `stripe` dependency**: Updated `requirements.txt`.
  2. **Created Stripe Webhook Router**: Added `backend/app/routers/stripe_webhook.py` which listens to `/api/webhooks/stripe`.
     - Validates the Stripe signature using `STRIPE_WEBHOOK_SECRET`.
     - Extracts ONLY non-PII fields: `customer_id`, `transaction_id`, and `amount_total`.
     - Does not log or extract names, emails, addresses, or payment card details.
  3. **Transaction Service**: Created `backend/app/services/transaction_service.py` to handle the pseudo-anonymous data storage.
  4. **App Registration**: Registered the `stripe_webhook` router in `backend/app/main.py`.
  5. **Testing**: Implemented TDD-based tests in `backend/tests/test_stripe_webhook.py` to ensure signature validation and zero-PII data extraction logic work correctly.
- **Impact**:
  - Increases the security of the FonMaYang system by minimizing the storage of sensitive financial information.
  - Safely processes one-time payments and subscriptions.
  - Complies with data minimization and GDPR/PDPA best practices.

---

## Issue #193: Pseudonymous Authentication & Magic Link Token Generator
- **Objective**: Generate a unique token upon a successful donation to persist session without PII.
- **Implementation**: 
  - Created `Donor` model in `models.py` with `token`, `hashed_transaction_id`, `amount`, and `timestamp`.
  - Added `POST /auth/generate-token` endpoint that accepts donation metadata and returns a `Fon-XXXX-XXXX` format token.
  - Generates token using cryptographic `secrets.choice`.

## Issue #194: Two-Factor Financial Account Recovery Flow
- **Objective**: Recover an account using donation metadata without exposing raw transaction IDs.
- **Implementation**:
  - `POST /auth/recover` endpoint accepts `transaction_id`, `amount`, and `timestamp`.
  - DB queries by exact `amount`, filters by timestamp (naive 1-second tolerance), and uses `bcrypt.checkpw` to verify the transaction ID hash.
  - If successful, returns the magic token.

## Testing (MR 3)
- Implemented `test_auth_recovery.py` which validates:
  1. Token generation on donation success.
  2. Successful recovery with exact transaction data.
  3. Rejection of invalid transaction IDs.
  4. Rejection of invalid amounts.
- Tests executed and passed successfully.

---

# Walkthrough for MR 4 (Issues #191, #195)

## 1. Budget Jars State Machine & Allocation Strategy
- **File**: `backend/app/services/budget_jars.py`
- **Description**: Implemented the `BudgetJarManager` with `BudgetState`. It correctly routes incoming donations (add_donation) into salary (50%), infra (30%), and API (20%) jars.
- **Deduction**: Implemented a `deduct_daily_costs` method to subtract daily burn from each respective jar.

## 2. Dynamic Runway Countdown Engine
- **File**: `backend/app/services/runway_engine.py`
- **Description**: Implemented `RunwayEngine.calculate_remaining_days(current_budget, fixed_daily_cost, variable_usage_cost)`.
- **Handling Limits**: Handles division by zero (returning `inf` if no costs) and correctly calculates total run days.

## 3. Real-time Streaming API (SSE)
- **File**: `backend/app/routers/runway.py`
- **Description**: Exposed `/api/v1/runway/stream` endpoint delivering Sever-Sent Events (SSE) representing real-time updates for `remaining_days`, `budget`, and `daily_burn`.
- **Integration**: Added `app.include_router(runway.router)` in `backend/app/main.py`.

## TDD Implementation (MR 4)
- Fully covered the new logic in:
  - `backend/tests/test_budget_jars.py`
  - `backend/tests/test_runway_engine.py`
  - `backend/tests/test_runway_sse.py`
- Tests pass cleanly, validating both correct values and edge cases (like zero cost).
