# Manual Verification Plan: GCP Billing Cache & PostgreSQL Historical Archiving

- **Merged PR / Issue ID**: MR !105 (Closes #249, #339)
- **Integration Target**: `dev` (Merged), preparing for `staging` & `production`
- **Updated Date**: 2026-09-26

---

## 🌐 Environment Matrix & Base Configuration

| Parameter / Feature | Local / Dev (`development`) | Staging (`staging`) | Production (`production`) |
| :--- | :--- | :--- | :--- |
| **Backend Base URL** | `http://localhost:8000` | `https://fontokmai-api-staging-xxxx-as.a.run.app` | `https://fontokmai-api-xxxx-as.a.run.app` |
| **Frontend Base URL** | `http://localhost:3000` | `https://staging.fonmayang.com` (or Vercel preview) | `https://fonmayang.com` |
| **Default Data Mode** | **Mock Data** (`is_mock=true`) | **Real BigQuery** (`is_mock=false`) | **Real BigQuery** (`is_mock=false`) |
| **Neon Policy Override** | Ignored unless `FORCE_GCP_REAL_DATA=true` | Consults `system_config.gcp_force_real_data` | Consults `system_config.gcp_force_real_data` |
| **Auto-Freeze to DB** | Disabled for mock data | Enabled for finalized past months | Enabled for finalized past months |
| **Cache Invalidation** | `force_refresh=true` (TTL: 900s) | `force_refresh=true` (TTL: 900s) | `force_refresh=true` (TTL: 900s) |

---

## 📌 Prerequisites & Secrets Setup

Before executing verification, ensure you have the appropriate `CRON_SECRET` for the target environment:

```bash
# 1. Local / Development
export TARGET_ENV="dev"
export BASE_URL="http://localhost:8000"
export CRON_SECRET="test_secret_123"

# 2. Staging Environment
# export TARGET_ENV="staging"
# export BASE_URL="https://fontokmai-api-staging-xxxx-as.a.run.app"
# export CRON_SECRET="<STAGING_CRON_SECRET_FROM_SECRET_MANAGER>"

# 3. Production Environment
# export TARGET_ENV="production"
# export BASE_URL="https://fontokmai-api-xxxx-as.a.run.app"
# export CRON_SECRET="<PROD_CRON_SECRET_FROM_SECRET_MANAGER>"
```

---

## 🧪 Verification Scenarios by Environment

### Scenario 1: Development / Local Environment Verification
**Focus:** Mock fallback safety, in-memory cache TTL, manual force refresh, and mock write protection.

1. **Step 1: Current Month Mock & In-Memory Cache**
   ```bash
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=current_month"
   ```
   - **Expected Outcome:**
     - HTTP Status: `200 OK`
     - Response: `{"is_mock": true, "currency": "THB", ...}`
     - Backend Logs: `[GCP_BILLING] Mock-only mode enabled; returning mock data without querying BigQuery`
   - **Step 1.1: Immediate consecutive call:**
     - Backend Logs: `[GCP_BILLING] Cache hit for current_month:False (age=...s)`.

2. **Step 2: Force Refresh Bypass**
   ```bash
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=current_month&force_refresh=true"
   ```
   - **Expected Outcome:** Cache is bypassed, returning fresh mock breakdown.

3. **Step 3: Verification that Mock Data is NEVER Persisted to DB**
   ```bash
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=2026-05"
   ```
   - **Expected Outcome:**
     - HTTP Status: `200 OK` with `is_mock: true`.
     - DB Check: Table `gcp_billing_history` must **NOT** contain any row for `month = '2026-05'`.

---

### Scenario 2: Staging Environment Verification
**Focus:** Cloud Run connection to BigQuery, Neon DB policy override toggle, and DB auto-freeze validation.

1. **Step 1: Verify Real Data Fetching on Staging**
   ```bash
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=current_month"
   ```
   - **Expected Outcome:**
     - HTTP Status: `200 OK`
     - Response: `is_mock: false`, `total_thb > 0`
     - Cloud Run Logs: `[GCP_BILLING] BigQuery query returned X rows`

2. **Step 2: Verify Past Month Auto-Freeze & Read-Through Archive**
   *Choose a finalized past invoice month (e.g. `2026-07`):*
   ```bash
   # First request (fetches from BigQuery and archives to Neon PostgreSQL):
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=2026-07"
   ```
   - Cloud Run Logs: `[GCP_BILLING] Archived finalized billing data to DB for month=2026-07`

   ```bash
   # Second request (must be served purely from PostgreSQL DB archive):
   curl -s -H "x-cron-secret: ${CRON_SECRET}" "${BASE_URL}/api/v1/metrics/gcp-costs?period=2026-07"
   ```
   - Cloud Run Logs: `[GCP_BILLING] Returning archived cost from DB for month=2026-07` (Zero BigQuery queries).

3. **Step 3: Test Neon SystemConfig Toggle (Kill-switch)**
   - When key `gcp_force_real_data` in Neon table `system_config` is set to `"false"`, staging immediately falls back to mock mode without redeployment.

---

### Scenario 3: Production Environment Verification
**Focus:** Unit economics integrity, concurrent yearly aggregation latency, security authorization, and UI responsiveness.

1. **Step 1: Concurrent Yearly Cost Aggregation Latency (`asyncio.gather`)**
   ```bash
   time curl -s "${BASE_URL}/api/v1/metrics/cost/yearly?year=2026"
   ```
   - **Expected Outcome:**
     - Latency: **< 1.5 seconds** (previously ~9-10 seconds serial execution).
     - Response: Contains 12-month array `monthly_cost_breakdown`.
     - Months prior to current month load directly from PostgreSQL archive.

2. **Step 2: Historical Cost Endpoint Fix (`/cost`)**
   ```bash
   curl -s "${BASE_URL}/api/v1/metrics/cost?month=2026-07"
   ```
   - **Expected Outcome:**
     - Field `"month"` is `"2026-07"`.
     - `gcp_cost_thb` matches the finalized GCP billing total stored in `gcp_billing_history`.

3. **Step 3: Security & Authorization Boundary Checks**
   ```bash
   # 1. Missing header must fail
   curl -s -I "${BASE_URL}/api/v1/metrics/gcp-costs"
   # HTTP/2 401 Unauthorized

   # 2. Timing attack / invalid secret must fail
   curl -s -I -H "x-cron-secret: wrong_secret_attacker" "${BASE_URL}/api/v1/metrics/gcp-costs"
   # HTTP/2 401 Unauthorized
   ```

4. **Step 4: Web Dashboard UI Verification (Production & Staging)**
   1. Navigate to `/admin/metrics` on the Web Dashboard.
   2. Verify the **GCP Infrastructure Cost Card** displays real values with currency `THB`.
   3. Check that the "Mock Data" badge is **NOT** present on Staging/Production.
   4. Click the manual refresh button (`#gcp-cost-refresh-btn`):
      - Button locks (`disabled=true`) immediately with spinning icon.
      - Network inspector shows single request to `/api/metrics/gcp-costs?period=...&force_refresh=true`.
      - Values update without full page re-render.

---

## 📸 Automated Test Proof (Regression Suite)

All 87 automated unit, integration, and security tests pass cleanly:

```text
backend/tests/test_gcp_billing.py:   22 passed (Cache hit, force_refresh, leap years, auto-freeze)
backend/tests/test_metrics.py:       20 passed (Yearly asyncio.gather, cron metrics)
backend/tests/test_scheduler.py:     18 passed (Routine triggers, sync_gcp_billing_history_routine)
backend/tests/test_api_security.py:  26 passed (SQLi, XSS, constant-time compare, fuzzing)
backend/tests/test_deploy_env_sync.py: 1 passed (Env variables synchronization)
======================== 87 passed in 4.07s ========================
```
