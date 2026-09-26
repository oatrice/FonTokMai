# Manual Verification Guide: GCP Billing Cache & PostgreSQL Historical Archiving

## Feature Scope
- **Issue #249**: Add caching for GCP billing query results to reduce BigQuery cost
- **Issue #339**: Implement GCP Billing Cache and Database Archive for Historical Costs

---

## 1. Prerequisites
- Backend running locally (`uvicorn app.main:app --port 8000`) or in Docker.
- Environment variables:
  - `CRON_SECRET=test_secret_123`
  - `GCP_PROJECT_ID=test-project`
  - `GCP_BILLING_BIGQUERY_DATASET=test-dataset`

---

## 2. Verification Steps

### Step 1: In-Memory Cache Verification (Current Month)
**Goal:** Verify consecutive requests do not re-run BigQuery within the 15-minute TTL.

1. Send initial request for current month:
   ```bash
   curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month"
   ```
2. Inspect backend logs:
   - Expected: `[GCP_BILLING] get_current_month_costs period=current_month ...` (Cache miss / BigQuery queried or mock returned).
3. Send second identical request immediately:
   ```bash
   curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month"
   ```
4. Inspect backend logs:
   - Expected: `[GCP_BILLING] Cache hit for current_month:... (age=...s)`. BigQuery is bypassed.

---

### Step 2: Manual Force Refresh Bypass
**Goal:** Verify `force_refresh=true` invalidates/bypasses the in-memory cache.

1. Send request with `force_refresh=true`:
   ```bash
   curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month&force_refresh=true"
   ```
2. Inspect backend logs:
   - Expected: Cache bypassed and BigQuery re-queried fresh.

---

### Step 3: Database Archiving & Read-Through Auto-Freeze (Past Months)
**Goal:** Verify historical months (`YYYY-MM`) are automatically archived to PostgreSQL and served with 0 BigQuery cost on subsequent requests.

1. Request a finalized past month (e.g. `2026-07`):
   ```bash
   curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=2026-07"
   ```
2. Inspect backend logs & PostgreSQL:
   - If not in DB: Fetches once, then `[GCP_BILLING] Archived finalized billing data to DB for month=2026-07`.
3. Request the same past month again:
   ```bash
   curl -s -H "x-cron-secret: test_secret_123" "http://localhost:8000/api/v1/metrics/gcp-costs?period=2026-07"
   ```
4. Inspect backend logs:
   - Expected: `[GCP_BILLING] Returning archived cost from DB for month=2026-07`. BigQuery is NEVER queried.

---

### Step 4: Historical Cost Endpoint Fix Verification
**Goal:** Verify `/cost` and `/cost/yearly` correctly query the requested historical month rather than hardcoded `current_month`.

1. Request historical cost report for a previous month:
   ```bash
   curl -s "http://localhost:8000/api/v1/metrics/cost?month=2026-07"
   ```
   - Verify `month` in the JSON response is `"2026-07"` and `gcp_cost_thb` reflects the archived 2026-07 GCP cost.
2. Request yearly cost breakdown:
   ```bash
   curl -s "http://localhost:8000/api/v1/metrics/cost/yearly?year=2026"
   ```
   - Verify each month up to the current month contains its specific monthly GCP cost breakdown from PostgreSQL archive.

---

### Step 5: Frontend UI Manual Refresh
1. Open the Web Dashboard at `/admin/metrics` or the main dashboard where `GCPCostBreakdown` is mounted.
2. Click the refresh button (`#gcp-cost-refresh-btn`).
3. Check browser DevTools Network tab:
   - Verify request is sent to `/api/metrics/gcp-costs?period=...&force_refresh=true`.
