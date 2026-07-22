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
