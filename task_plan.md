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

### [ ] Phase 5: Resiliency & Feature Controls (MR 5)
- **Issues**: #196, #197
- **Tasks**:
  - [ ] Build Dynamic Circuit Breaker middleware (downgrade on Jar.HP <= 0).
  - [ ] Implement Emergency Overdrive toggle (Invincible Mode).

### [ ] Phase 6: Milestone Presentation & Security Lock (MR 6)
- **Issues**: #198
- **Tasks**:
  - [ ] Build progress bar UI and data endpoints.
  - [ ] Implement donation lock kill-switch.

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
