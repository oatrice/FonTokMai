# Task Plan: Gamified Financial Transparency System

## Goal
Implement issues #190 to #198 as part of the Gamified Financial Transparency System, properly batched into 6 Merge Requests to minimize risk and optimize review cycles.

## Phases

### [x] Phase 1: Billing Data Foundation (MR 1)
- **Issues**: #190
- **Tasks**:
  - [x] Implement GCP Cloud Billing & AWS Cost Explorer API integration.
  - [x] Setup cost aggregation pipeline (Baseline vs Variable metrics).

### [ ] Phase 2: Zero-PII Stripe Payment Webhook (MR 2)
- **Issues**: #192
- **Tasks**:
  - [ ] Create Stripe webhook listener.
  - [ ] Extract and store `Stripe_Customer_ID` and `Transaction_ID` with zero PII.

### [ ] Phase 3: Anonymous Auth & Recovery Flow (MR 3)
- **Issues**: #193, #194
- **Tasks**:
  - [ ] Generate `Fon-XXXX-XXXX` tokens on donation event from MR 2.
  - [ ] Implement magic link token auth with Local Storage.
  - [ ] Implement 3-point recovery API (Transaction ID Hash, Timestamp, Amount).

### [ ] Phase 4: Budget Jars & Runway Engine (MR 4)
- **Issues**: #191, #195
- **Tasks**:
  - [ ] Implement Budget Jars state machine and allocation split based on MR 2 incoming payments.
  - [ ] Build Runway countdown engine math using MR 1 cost metrics.
  - [ ] Setup SSE/WebSockets broadcast for runway updates.

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
