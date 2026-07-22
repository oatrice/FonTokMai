# Task Plan: Gamified Financial Transparency System

## Goal
Implement issues #190 to #198 as part of the Gamified Financial Transparency System, properly batched into 6 Merge Requests to minimize risk and optimize review cycles.

## Phases

### [x] Phase 1: Billing Data Foundation (MR 1)
- **Issues**: #190
- **Tasks**:
  - [x] Implement GCP Cloud Billing & AWS Cost Explorer API integration.
  - [x] Setup cost aggregation pipeline (Baseline vs Variable metrics).

### [x] Phase 2: Zero-PII Stripe Payment Webhook (MR 2)
- **Issues**: #192
- **Tasks**:
  - [x] Create Stripe webhook listener.
  - [x] Extract and store `Stripe_Customer_ID` and `Transaction_ID` with zero PII.

### [x] Phase 3: Anonymous Auth & Recovery Flow (MR 3)
- **Issues**: #193, #194
- **Tasks**:
  - [x] Generate `Fon-XXXX-XXXX` tokens on donation event from MR 2.
  - [x] Implement magic link token auth with Local Storage.
  - [x] Implement 3-point recovery API (Transaction ID Hash, Timestamp, Amount).

### [x] Phase 4: Budget Jars & Runway Engine (MR 4)
- **Issues**: #191, #195
- **Tasks**:
  - [x] Implement Budget Jars state machine and allocation split based on MR 2 incoming payments.
  - [x] Build Runway countdown engine math using MR 1 cost metrics.
  - [x] Setup SSE/WebSockets broadcast for runway updates.

### [x] Phase 5: Resiliency & Feature Controls (MR 5)
- **Issues**: #196, #197
- **Tasks**:
  - [x] Build Dynamic Circuit Breaker middleware (downgrade on Jar.HP <= 0).
  - [x] Implement Emergency Overdrive toggle (Invincible Mode).

### [ ] Phase 6: Milestone Presentation & Security Lock (MR 6)
- **Issues**: #198
- **Tasks**:
  - [ ] Build progress bar UI and data endpoints.
  - [ ] Implement donation lock kill-switch.

---

# Task Plan: MR 2 - Zero-PII Stripe Webhook Listener & Transaction Logger (Issue #192)

## Overview
Implement a secure Stripe webhook listener that processes payment and subscription events while storing zero PII (Personally Identifiable Information).

## Acceptance Criteria
- [x] **Signature Validation:** Webhook receiver successfully validates the signature of incoming Stripe webhooks using the configured webhook secret.
- [x] **Event Processing:** Checkout session events (one-time & subscription) such as `checkout.session.completed` are successfully processed.
- [x] **Data Extraction:** Extracts only necessary, pseudonymous fields: `Stripe_Customer_ID` (customer), `Transaction_ID` (payment_intent / subscription), and donation amount (amount_total).
- [x] **Zero PII Storage:** Database record saves ONLY the extracted non-PII fields. Billing names, emails, addresses, and payment card details MUST NOT be stored.
- [x] **Tests:** Webhook handler is thoroughly tested with invalid signatures, missing payloads, and valid zero-PII extraction scenarios.

## Developer Tasks (TDD)
1. Write a failing test for Stripe webhook signature validation (400 Bad Request on invalid signature).
2. Write a failing test for a valid webhook payload ensuring only `Stripe_Customer_ID`, `Transaction_ID`, and amount are saved to the database.
3. Implement the Stripe webhook endpoint (e.g., `/api/webhooks/stripe`).
4. Implement the service/repository to save transaction data.
5. Make tests pass and refactor.
6. Verify no PII is logged or passed to the database layer.

## QA Tasks
1. Run all tests with `pytest tests/ -v`.
2. Generate `walkthrough.md` and `manual_verification.md` reflecting the testing and verification process.

---

# Task Plan for MR 3 (Issues #193, #194)

## Overview
Implement Pseudonymous Authentication & Magic Link Token Generator (#193) and Two-Factor Financial Account Recovery Flow (#194).

## 1. BA Agent Role (Completed)
- Read issues #193 and #194.
- Created `task_plan.md`.

## 2. Developer Agent Role
### Issue #193: Anon Auth & Recovery (Auth generation)
- Generate a cryptographically random token upon a successful donation.
- The token will be used as a "Magic Link" parameter and stored in Local Storage on the client.
- **Backend changes**:
  - Add auth token field to user/donor model.
  - Create a new router for authentication (`backend/app/routers/auth.py`).
  - Implement token generation logic (e.g., `Fon-{random}`).
  - Add tests in `backend/tests/test_auth.py` (TDD: Red-Green-Refactor).

### Issue #194: Two-Factor Financial Account Recovery Flow
- Recovery via `Transaction_ID`, `Timestamp` of donation, and `Exact Amount`.
- **Backend changes**:
  - Store `Transaction_ID` securely (hashed). Update schema/model in `backend/app/models.py`.
  - Add a recovery API endpoint to verify transaction data.
  - Implement hashing/verification logic.
  - Add tests in `backend/tests/test_recovery.py` (TDD: Red-Green-Refactor).

## 3. QA Agent Role
- Run `pytest backend/tests/ -v`.
- Document walkthrough and validation in `walkthrough.md` and `manual_verification.md`.

## 4. MR Manager Agent Role
- Push branch `feat/193-194-anon-auth-recovery`.
- Compose MR description embedding the markdown files.
- Submit MR & Call `notify_pending_review` and `notify_task_complete`.

---

# Task Plan for MR 4 (Issues #191, #195)

## Issue 195: [Backend] Budget Jars State Machine & Allocation Strategy
1. **Model/Data Structure**: Define the `BudgetJar` and `AllocationStrategy`.
   - Jars: Dev Salary, Infrastructure, API.
   - Percentages for each jar.
2. **Transaction Handler**: Split incoming donations (e.g. from Stripe) into respective jars.
3. **Time Decay / Deductions**: Implement daily deduction routines (e.g., daily salary jar reductions).
4. **Unit Tests**:
   - Verify state machine routes donations correctly.
   - Verify daily time-decay cost deductions compute correctly.

## Issue 191: [Architecture] Dynamic Runway Countdown Engine
1. **Runway Engine**: Implement formula: `Remaining Days = Current Budget / (Fixed Daily Cost + Variable Usage Cost)`.
2. **Cost Aggregator Integration**: Connect engine to GCP/AWS cost data (or mock/interfaces if not fully implemented).
3. **Real-time Endpoint**: Build SSE or WebSocket endpoint for live runway updates.
4. **Unit Tests**:
   - Verify formula under various scenarios.
   - Verify SSE/WebSocket endpoint functions and streams updates.

## Execution (TDD)
- [x] Write failing tests for 195.
- [x] Implement 195.
- [x] Refactor 195.
- [x] Write failing tests for 191.
- [x] Implement 191.
- [x] Refactor 191.

---

# Task Plan for MR 5 (Issues #196, #197: Resiliency & Feature Controls)

## Issue 196: Dynamic Feature Flag & Circuit Breaker System
**Acceptance Criteria:**
- [ ] Circuit breaker correctly triggers fallback when Jar HP is <= 0.
- [ ] Middleware handles fallback transitions seamlessly without crashing the bot/application.
- [ ] System automatically recovers the paid features once the jar is funded again.

**Implementation Steps:**
- Create a `CircuitBreaker` class or middleware logic in `backend/app/services` or `backend/app/middleware`.
- Add logic to check a Jar's HP (balance).
- Wrap external API calls (e.g., weather API) with the Circuit Breaker.
- Provide a fallback response when the Circuit Breaker is triggered.

## Issue 197: Emergency Overdrive Mode (Free Period Bypass)
**Acceptance Criteria:**
- [ ] Admin command or flag successfully activates Emergency Overdrive.
- [ ] When active, circuit breakers are bypassed and paid features are forced on.
- [ ] Countdown UI displays appropriate emergency status/invincible indicator.

**Implementation Steps:**
- Add an `emergency_overdrive` flag to the system configuration (e.g., in a settings table or config).
- Update the Circuit Breaker logic to bypass the `Jar.HP <= 0` check if `emergency_overdrive` is true.
- Ensure that the runway decay is frozen when the flag is active.
