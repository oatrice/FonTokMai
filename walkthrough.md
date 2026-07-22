# QA Walkthrough

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

## Testing
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

## TDD Implementation
- Fully covered the new logic in:
  - `backend/tests/test_budget_jars.py`
  - `backend/tests/test_runway_engine.py`
  - `backend/tests/test_runway_sse.py`
- Tests pass cleanly, validating both correct values and edge cases (like zero cost).
