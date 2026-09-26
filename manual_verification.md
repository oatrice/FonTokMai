# Manual Verification Plan: GCP Billing Cache & PostgreSQL Historical Archiving

- **Branch**: `feat/339-249-gcp-billing-cache-archive`
- **MR / Issue ID**: MR !105 (Closes #249, #339)
- **Date**: 2026-09-26

---

## 📌 Prerequisites & Environment Setup
1. Environment variables:
   ```bash
   export CRON_SECRET=test_secret_123
   export GCP_PROJECT_ID=test-project
   export GCP_BILLING_BIGQUERY_DATASET=test-dataset
   ```
2. Launch server locally:
   ```bash
   poetry run uvicorn backend.app.main:app --reload --port 8000
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: In-Memory Cache Verification (Current Month Happy Path)
- **Goal**: Verify consecutive requests do not re-run BigQuery within the 15-minute TTL.
- **Steps**:
  1. Initial request:
     ```bash
     curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month"
     ```
  2. Immediate consecutive request:
     ```bash
     curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month"
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Backend Log: `[GCP_BILLING] Cache hit for current_month:... (age=...s)`. BigQuery is bypassed.

---

### Scenario 2: Manual Force Refresh Bypass
- **Goal**: Verify `force_refresh=true` invalidates/bypasses the in-memory cache and re-queries BigQuery.
- **Steps**:
  ```bash
  curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month&force_refresh=true"
  ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Backend Log: Cache bypassed and BigQuery re-queried fresh.

---

### Scenario 3: Database Archiving & Read-Through Auto-Freeze (Past Months)
- **Goal**: Verify historical months (`YYYY-MM`) are automatically archived to PostgreSQL and served with 0 BigQuery cost on subsequent requests.
- **Steps**:
  1. Request finalized past month (`2026-07`):
     ```bash
     curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=2026-07"
     ```
  2. Request the same past month again.
- **Expected Outcome**:
  - Request 1: Fetches from source, logs `[GCP_BILLING] Archived finalized billing data to DB for month=2026-07`.
  - Request 2: Logs `[GCP_BILLING] Returning archived cost from DB for month=2026-07`. BigQuery is NEVER queried.

---

### Scenario 4: Concurrent Yearly Endpoint & Historical Cost Accuracy
- **Goal**: Verify `/cost` and `/cost/yearly` query historical months correctly via `asyncio.gather` concurrency.
- **Steps**:
  ```bash
  curl -s "http://localhost:8000/api/v1/metrics/cost?month=2026-07"
  curl -s "http://localhost:8000/api/v1/metrics/cost/yearly?year=2026"
  ```
- **Expected Outcome**:
  - 12 months gathered in parallel without N+1 sequential blocking.
  - HTTP Status: `200 OK`

---

### Scenario 5: Security & Injection Resistance
- **Goal**: Verify authorization enforcement, SQL injection immunity, and API fuzzing resiliency.
- **Steps**:
  1. Missing Header:
     ```bash
     curl -s -I "http://localhost:8000/api/v1/metrics/gcp-costs"
     # HTTP 401 Unauthorized
     ```
  2. SQL injection payload in period:
     ```bash
     curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=2026';DROP%20TABLE"
     # Handled safely without 500 server crash
     ```

---

### Scenario 6: Frontend UI Manual Refresh & Race Condition Protection
- **Goal**: Verify UI refresh button locks during flight and indicates active loading state.
- **Steps**:
  1. Open dashboard at `/admin/metrics` with `GCPCostBreakdown`.
  2. Click refresh button (`#gcp-cost-refresh-btn`).
- **Expected Outcome**:
  - Button enters `disabled` state with `isRefreshing` spinner.
  - SWR cache updates seamlessly upon response.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Test Results**:
  ```text
  backend/tests/test_gcp_billing.py: 22 passed
  backend/tests/test_metrics.py: 20 passed
  backend/tests/test_scheduler.py: 15 passed
  backend/tests/test_api_security.py: 26 passed
  Total: 83 passed, 0 failed in 7.2s
  ```
