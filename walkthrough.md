# Walkthrough: Dashboard UX/UI & Zero-PII Token Recovery Batch

This Merge Request addresses three primary objectives within the frontend dashboard components:

## 1. UX Terminology Updates (#204)
Technical jargon in `FinancialDashboard.tsx` and `RunwayCounter.tsx` has been replaced with user-friendly terminology to enhance clarity for non-technical sponsors:
- `OVERDRIVE MODE` → `Extended Lifespan Mode / โหมดต่ออายุระบบฉุกเฉิน`
- `CIRCUIT BREAKER ACTIVE` → `Cached Weather Data Mode / ใช้ข้อมูลพยากรณ์สำรอง`

## 2. Dashboard View Modes (#209)
The `RunwayCounter.tsx` component was entirely refactored to support three interactive view modes:
- **Numeric View**: Standard stat block.
- **Storytelling View**: Conversational explanation of runway duration.
- **Compact View**: Minimalist ticker layout.
State is seamlessly animated via `framer-motion` (`AnimatePresence`) and user preferences are persistently stored in the browser's `localStorage` (`runwayViewMode`).

## 3. Token Recovery Modal (#236)
A new zero-PII recovery interface (`TokenRecoveryModal.tsx`) was introduced to allow sponsors to reclaim lost access tokens using their transaction receipt details:
- **Inputs**: `tx_hash`, `timestamp`, and `amount`.
- **Integration**: Securely POSTs to the `/api/v1/auth/recover` endpoint.
- **Robust Feedback**: Handles and visualizes API validation errors gracefully, and prominently displays the recovered `sk_test_...` access token upon success.
- **Testing**: Includes a comprehensive Jest test suite (`TokenRecoveryModal.test.tsx`) verifying form rendering, submission behaviors, and error/success states.
