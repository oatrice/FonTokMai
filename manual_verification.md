# Manual Verification Guide: Frontend Financial Dashboard Batch MR (#227, #146, #147)

This document provides step-by-step instructions to manually verify that `FinancialDashboard.tsx` dynamically consumes `/api/runway`, mock budget jars are removed, and budget allocations & runway countdown timers render cleanly.

## Prerequisites
- Node.js & npm installed
- Next.js development server or local build

## Verification Steps

### 1. Automated Unit & Build Verification
Run the following commands in terminal:

```bash
# 1. Frontend Unit Tests
npm test --prefix frontend

# 2. Frontend Production Build Check
npm run build --prefix frontend

# 3. Cloud Run Deploy Env Synchronization Check
pytest backend/tests/test_deploy_env_sync.py
```

**Expected Outcome:**
- All 5 Jest unit tests pass cleanly (`FinancialDashboard.test.tsx` and `GlassNavbar.test.tsx`).
- Next.js build succeeds with static/dynamic route compilation without TypeScript errors.
- `test_deploy_env_sync.py` passes with 100% success.

---

### 2. Manual UI Verification on Home Page (`/`)

1. Start the Next.js frontend local dev server:
   ```bash
   npm run dev --prefix frontend
   ```
2. Open browser at `http://localhost:3000/`.
3. Check the **Financial Runway Hero Stats**:
   - Verify that **Live Runway Days**, **Daily Burn (฿/day)**, and **Total Reserve Vault (฿)** reflect dynamic data from `/api/runway`.
   - Verify that the badge shows `Live Math` (or `Syncing...` while loading).
4. Check the **Budget Jars State Machine**:
   - Verify that hardcoded jars (*Infrastructure Jar*, *Developer Salary Jar*, *API & Data Services*) are **gone**.
   - Verify that active dynamic budget jars render:
     - **Cloud Run Infrastructure (50%)**
     - **TMD Radar & Weather APIs (30%)**
     - **Emergency Reserve Jar (20%)**
   - Verify allocated balances match the total reserve split.
5. Check **Interactive Elements**:
   - Click **Sync Jars** button to verify SWR revalidation.
   - Toggle **Emergency Invincible Mode** switch to verify status changes to `OVERDRIVE`.
   - Click **Contribute to Milestone** button to verify `DonationModal` opens smoothly.

---

### 3. Manual Verification on Dashboard Page (`/dashboard`)

1. Navigate to `http://localhost:3000/dashboard`.
2. Verify that `RunwayCounter.tsx` and `BudgetJars.tsx` display consistent runway days and jar percentages matching the home page.
