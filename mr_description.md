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

---

# Manual Verification Plan - Dashboard UX/UI & Zero-PII Token Recovery Batch

- **Branch**: `feat/dashboard-ux-recovery-batch`
- **MR / Issue ID**: `#204, #209, #236`
- **Date**: `2026-08-02`

---

## 📌 Prerequisites & Environment Setup
1. Node.js environment configured for the Next.js frontend.
2. Shell commands to launch server locally:
   ```bash
   cd frontend
   npm run dev
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: UX Terminology Updates (#204)
- **Goal**: Verify that confusing technical terms have been replaced.
- **Steps**:
  1. Open the Financial Dashboard page (`http://localhost:3000` or equivalent route).
  2. Observe the badge and text states.
- **Expected Outcome**:
  - `OVERDRIVE MODE` should be replaced with `Extended Lifespan Mode / โหมดต่ออายุระบบฉุกเฉิน`.
  - `CIRCUIT BREAKER ACTIVE` should be replaced with `Cached Weather Data Mode / ใช้ข้อมูลพยากรณ์สำรอง`.

---

### Scenario 2: Runway Counter View Modes (#209)
- **Goal**: Verify that the 3 viewing modes work and animations are smooth.
- **Steps**:
  1. Locate the Runway Counter widget on the Financial Dashboard.
  2. Click the gear or toggle button (if present) or click the component itself to cycle modes (Numeric -> Storytelling -> Compact).
  3. Reload the page.
- **Expected Outcome**:
  - Transitions between modes are smoothly animated via `framer-motion`.
  - The selected mode persists across page reloads (saved in `localStorage` under `runwayViewMode`).

---

### Scenario 3: Token Recovery Modal - Successful Recovery (#236)
- **Goal**: Verify that the Token Recovery Modal accepts valid inputs and returns a token.
- **Steps**:
  1. On the Financial Dashboard, click the "Start Token Recovery" button.
  2. In the modal, enter a mock `tx_hash` (e.g. `0x123`), `timestamp` (e.g. `1690000000`), and `amount` (e.g. `500`).
  3. Click "Recover Token".
  4. (For full verification, a mock backend response or dev environment pointing to `/api/v1/auth/recover` is required).
- **Expected Outcome**:
  - The modal transitions to a success state displaying the recovered token (e.g., `sk_test_...`).

---

### Scenario 4: Token Recovery Modal - Error Handling (#236)
- **Goal**: Verify that the Token Recovery Modal handles invalid inputs gracefully.
- **Steps**:
  1. On the Financial Dashboard, click the "Start Token Recovery" button.
  2. Enter invalid details that the backend will reject.
  3. Click "Recover Token".
- **Expected Outcome**:
  - An error message appears in a red alert box within the modal (e.g., "Recovery failed. Invalid details.").
  - The form remains open for the user to try again.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `npm run test -- TokenRecoveryModal.test.tsx` result: `5 passed, 5 total`
  - Output Snippet:
    ```
    PASS src/components/dashboard/__tests__/TokenRecoveryModal.test.tsx
      TokenRecoveryModal
        ✓ does not render when isOpen is false
        ✓ renders the form inputs when isOpen is true
        ✓ shows error message on API failure
        ✓ shows recovered token on API success
        ✓ calls onClose when close button or overlay is clicked
    ```

---

Closes #204, Closes #209, Closes #236
