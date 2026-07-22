# Task Plan: Gamified Financial Transparency System

## Goal
Implement issues #190 to #198 as part of the Gamified Financial Transparency System, properly batched into 6 Merge Requests to minimize risk and optimize review cycles.

## Phases

### [ ] Phase 1: Billing Data Foundation (MR 1)
- **Issues**: #190
- **Tasks**:
  - [ ] Implement GCP Cloud Billing & AWS Cost Explorer API integration.
  - [ ] Setup aggregation pipeline (Baseline vs Variable costs).

### [ ] Phase 2: Stripe Payment Webhook (MR 2)
- **Issues**: #192
- **Tasks**:
  - [ ] Create Stripe webhook listener.
  - [ ] Extract and store `Stripe_Customer_ID` and `Transaction_ID` with zero PII.

### [ ] Phase 3: Anonymous Auth & Recovery Flow (MR 3)
- **Issues**: #193, #194
- **Tasks**:
  - [ ] Generate `Fon-XXXX-XXXX` tokens on donation.
  - [ ] Implement magic link token auth with Local Storage.
  - [ ] Implement 3-point recovery API (Transaction ID Hash, Timestamp, Amount).

### [ ] Phase 4: Budget Jars & Runway Engine (MR 4)
- **Issues**: #191, #195
- **Tasks**:
  - [ ] Implement Budget Jars state machine and allocation split.
  - [ ] Build Runway countdown engine math.
  - [ ] Setup SSE/WebSockets broadcast for runway updates.

### [ ] Phase 5: Resiliency & Feature Controls (MR 5)
- **Issues**: #196, #197
- **Tasks**:
  - [ ] Build Dynamic Circuit Breaker (downgrade on Jar.HP <= 0).
  - [ ] Implement Emergency Overdrive toggle (Invincible Mode).

### [ ] Phase 6: Milestone Presentation & Security Lock (MR 6)
- **Issues**: #198
- **Tasks**:
  - [ ] Build progress bar UI and data endpoints.
  - [ ] Implement donation lock kill-switch.
