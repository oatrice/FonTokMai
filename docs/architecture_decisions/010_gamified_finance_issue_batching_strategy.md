# ADR 010: Gamified Finance & Infrastructure Management Platform MR Batching Strategy

## Status
Proposed

## Context
We are implementing a new Gamified Financial Transparency System comprising 9 issues (#190 - #198). To ensure high-quality code reviews, prevent Large Merge Requests (MRs), and control system complexity, we must group these tasks logically. Large MRs increase deployment risk and review latency, while separate MRs for tightly-coupled components create integration overhead.

## Decision
We will partition the 9 issues into **6 distinct, sequential Merge Requests (MRs)** based on dependency order, security isolation, and feature cohesion:

```mermaid
graph TD
    MR1[MR 1: Billing & Cost Aggregator #190] --> MR4[MR 4: Jars State Machine & Runway Engine #191, #195]
    MR2[MR 2: Zero-PII Stripe Webhook #192] --> MR3[MR 3: Anon Auth & Recovery #193, #194]
    MR2 --> MR4
    MR4 --> MR5[MR 5: Circuit Breakers & Overdrive #196, #197]
    MR3 --> MR6[MR 6: Milestone Funding & Donation Lock #198]
    MR5 --> MR6
```

---

### MR 1: Billing Data Foundation
- **Issues**: 
  - [DevOps] GCP/AWS Billing API Integration & Cost Aggregator ([#190](https://gitlab.com/oatricedev/FonMaYang/-/work_items/190))
- **Scope**: 
  - Implement read-only clients for GCP Cloud Billing & AWS Cost Explorer.
  - Aggregation pipeline for baseline and variable costs stored in Firestore/Redis.
- **Rationale**: Isolates IAM configuration and external API integration tasks, establishing the cost database schema.

### MR 2: Stripe Payment Webhook
- **Issues**: 
  - [Security] Zero-PII Stripe Webhook Listener & Transaction Logger ([#192](https://gitlab.com/oatricedev/FonMaYang/-/work_items/192))
- **Scope**: 
  - Stripe webhook listener endpoint with signature verification.
  - Database logging storing only `Stripe_Customer_ID` and `Transaction_ID`.
- **Rationale**: Isolates payment processing and security validation to guarantee zero PII data persistence.

### MR 3: Anonymous Auth & Recovery Flow
- **Issues**: 
  - [Feature] Pseudonymous Authentication & Magic Link Token Generator ([#193](https://gitlab.com/oatricedev/FonMaYang/-/work_items/193))
  - [Security] Two-Factor Financial Account Recovery Flow ([#194](https://gitlab.com/oatricedev/FonMaYang/-/work_items/194))
- **Scope**: 
  - Token generator (`Fon-XXXX-XXXX`) and Local Storage auth persistence.
  - Hashing mechanism (Bcrypt/SHA-256 + Salt) for Transaction IDs.
  - 3-point recovery API (`Hashed_Transaction_ID` + `Timestamp` + `Exact Amount`).
- **Rationale**: Groups the complete anonymous identity and credentials lifecycle. Hashing verification code is kept near the authentication context.

### MR 4: Budget Jars & Runway Engine
- **Issues**: 
  - [Architecture] Dynamic Runway Countdown Engine ([#191](https://gitlab.com/oatricedev/FonMaYang/-/work_items/191))
  - [Backend] Budget Jars State Machine & Allocation Strategy ([#195](https://gitlab.com/oatricedev/FonMaYang/-/work_items/195))
- **Scope**: 
  - Multi-jar allocation splits and time-decay routine for Dev Salary.
  - Mathematical implementation of runway countdown.
  - Server-Sent Events (SSE) or WebSockets broadcast endpoint.
- **Rationale**: Pairs the runway engine with the budget source (Jars) that drives it. Directly consumes the cost metrics from MR 1.

### MR 5: Resiliency & Feature Controls
- **Issues**: 
  - [Architecture] Dynamic Feature Flag & Circuit Breaker System ([#196](https://gitlab.com/oatricedev/FonMaYang/-/work_items/196))
  - [Feature] Emergency Overdrive Mode (Free Period Bypass) ([#197](https://gitlab.com/oatricedev/FonMaYang/-/work_items/197))
- **Scope**: 
  - Middleware/Interceptors for API fallbacks when `Jar.HP <= 0`.
  - Override switch to force "Invincible Mode" (bypass circuit breakers, freeze runway).
- **Rationale**: Concentrates runtime middleware overrides and fallbacks together, ensuring both failure modes and admin bypasses can be tested concurrently.

### MR 6: Milestone Presentation & Security Lock
- **Issues**: 
  - [Feature] Anonymized Milestone Funding & Donation Lock Mechanism ([#198](https://gitlab.com/oatricedev/FonMaYang/-/work_items/198))
- **Scope**: 
  - Read-only progress bar data endpoints.
  - Kill-switch to anonymize leaderboards instantly.
  - Redirect logic to "Future Donor Waiting List".
- **Rationale**: Focuses on public gamification elements and their security panic buttons. Depends on the Auth (MR 3) and Jars (MR 4) models.

---

## Data Flow & Integration Points

To ensure smooth inter-module communication across MR releases:

1. **MR 1 → MR 4 (Cost Metrics Flow)**:
   - MR 1 stores aggregated daily/hourly costs (`baseline_cost`, `variable_cost`) in DB/Redis.
   - MR 4 reads these cost metrics to compute remaining runway: `Days = Total Budget / (Baseline + Variable)`.

2. **MR 2 → MR 3 & MR 4 (Payment Processing & Allocation Flow)**:
   - MR 2 receives Stripe Webhook events and logs Zero-PII records (`Stripe_Customer_ID`, `Transaction_ID`, `Amount`).
   - MR 3 registers event hooks to issue pseudonymous tokens (`Fon-XXXX-XXXX`) upon successful donation events logged by MR 2.
   - MR 4 listens to payment confirmation events to split incoming funds across budget jars according to allocation percentages.

3. **MR 4 → MR 5 (Jar Health & Circuit Breaker Interception)**:
   - MR 4 updates `Jar.HP` and calculates live runway updates.
   - MR 5 middleware checks `Jar.HP` on each external API request. If `Jar.HP <= 0`, it triggers fallback options (e.g., Open-Meteo).
   - MR 5 Emergency Overdrive flag bypasses `Jar.HP` checks and freezes runway decay.

4. **MR 3 & MR 4 & MR 5 → MR 6 (Public Presentation & Lock Controls)**:
   - MR 6 queries anonymized milestone totals (from MR 4) and user badges (from MR 3).
   - MR 6 Security Lock kill-switch immediately masks public leaderboards and overrides public endpoints.

---

## End-to-End Workflow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Donator as 💚 Donator
    participant Webhook as 💳 Stripe Webhook (MR 2)
    participant Auth as 🔑 Anon Auth (MR 3)
    participant Jars as 🏺 Budget Jars & Runway (MR 4)
    participant Cloud as ☁️ GCP/AWS Billing (MR 1)
    participant Breaker as ⚡ Circuit Breaker (MR 5)
    actor User as 🌧️ End User

    Cloud->>Jars: 1. Send daily aggregated infrastructure costs (Baseline & Variable)
    Donator->>Webhook: 2. Donate via Stripe (Zero-PII Checkout)
    Webhook->>Auth: 3. Trigger pseudonymous token generation (Fon-XXXX-XXXX)
    Webhook->>Jars: 4. Deposit funds & split across budget jars
    Jars->>User: 5. Broadcast live runway countdown updates (SSE/WebSocket)
    Breaker->>Jars: 6. Check Jar.HP before external API requests
    alt Jar.HP > 0
        Breaker->>User: Serve premium weather radar data
    else Jar.HP <= 0
        Breaker->>User: Fallback to free weather provider (Open-Meteo)
    end
```

---

## Persona & System Perspectives

To align system design with business and user value:

1. **Donator (ผู้บริจาค)**:
   - **Zero-PII Payments (#192)**: Donates via Stripe with 0 personal data stored in DB.
   - **Pseudonymous Tokens (#193)**: Receives a unique token (e.g. `Fon-8x9J-K2pL`) via magic link to access personal milestone dashboard without username/password.
   - **2FA Recovery (#194)**: Recovers lost token via 3-point verification (Hashed Transaction ID + Timestamp + Amount).
   - **Gamified Badges (#198)**: Views anonymized milestone progress and public impact.

2. **End User (ผู้ใช้ทั่วไป / คนดูเรดาร์)**:
   - **Live Runway Countdown (#191)**: Sees live server lifespan countdown via SSE/WebSocket ("Server runway: 42 days").
   - **Graceful Fallbacks (#196)**: Keeps receiving radar services seamlessly even when budget jars deplete (`Jar.HP <= 0`), falling back to free APIs.
   - **Crisis Guarantee (#197)**: Emergency Overdrive guarantees 100% premium service during severe storm events.

3. **BA / Product Owner**:
   - **Budget Jar Allocation (#195)**: Configures allocation percentages (Server, API, Dev salary) and tracks time decay.
   - **Emergency Overdrive Toggle (#197)**: System-wide override toggle for disaster response periods.
   - **Donation Lock & Kill-Switch (#198)**: Security kill-switch to mask leaderboards and divert traffic to waiting lists during security incidents.

4. **SA / DevOps**:
   - **Automated Cost Aggregation (#190)**: Integrates GCP/AWS billing APIs to calculate real Baseline vs Variable infrastructure costs.
   - **Circuit Breaker Middleware (#196)**: Intercepts API calls to fallback to free tier APIs upon jar exhaustion without system crashes.
   - **Zero-PII Data Hardening (#192, #194)**: Ensures database stores only hashed transaction markers and anonymous IDs.

---

## Consequences
- **Reviewability**: Each MR targets less than 300-500 lines of code changes (except for schema definitions), facilitating fast PR cycle times.
- **Verification**: Developers can write targeted mock tests for each MR context.
- **Dependency Flow**: Subsequent MRs can be built on top of the schemas and endpoints defined in earlier MRs.
