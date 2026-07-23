# Manual Verification Document - FonMaYang Frontend /dashboard

## 📋 Overview
This document outlines manual verification steps and test scenarios for verifying the FonMaYang Frontend Web Application `/dashboard` page and its associated components.

---

## 🧪 Verification Scenarios

### Scenario 1: Dark Glassmorphism Layout & Responsive UI
- **URL**: `http://localhost:3000/dashboard`
- **Steps**:
  1. Open browser to `/dashboard`.
  2. Verify dark backdrop with frosted glass effect (`backdrop-blur-md`, subtle border glow).
  3. Resize viewport to mobile view (375px width).
  4. Verify layout gracefully collapses into single column grid.
- **Expected Outcome**: UI is crisp, responsive, visually appealing with modern dark glass aesthetic.

### Scenario 2: Live Runway Counter & Budget Jars
- **Steps**:
  1. Inspect network tab to verify SWR polling request to `/api/runway` every 10-15 seconds.
  2. Observe live counter ticking down smoothly with client-side interpolation.
  3. Verify Budget Jars allocation percentages match total runway balance.
- **Expected Outcome**: Polling runs efficiently without memory leaks or excessive re-renders.

### Scenario 3: Milestone Progress & Donation Lock Kill-Switch
- **Steps**:
  1. Check Milestone Progress bar showing target funding vs current balance.
  2. When donation lock status is active (`is_locked: true`), verify "DONATION LOCKED" warning banner and disabled donation actions.
- **Expected Outcome**: Donation lock status is clearly communicated to users.
