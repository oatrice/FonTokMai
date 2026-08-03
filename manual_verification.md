# Manual Verification Plan - GCP Billing Policy Consistency

- **Branch**: `feat/dashboard-ux-recovery-batch`
- **MR / Issue ID**: `#211`
- **Date**: `2026-08-03`

---

## 📌 Prerequisites & Environment Setup
1. Backend local environment is configured and can start with Uvicorn.
2. Frontend local environment is configured and points to the local backend.
3. `DATABASE_URL` is available for the target environment:
   - local/dev may use Neon or local DB
   - staging/prod should use Neon Postgres
4. Relevant env vars:
   - `ENVIRONMENT`
   - `FORCE_GCP_REAL_DATA`
   - `GCP_PROJECT_ID`
   - `GCP_BILLING_BIGQUERY_DATASET`
   - `CRON_SECRET`
5. Start backend:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
6. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Local Mock-Only Path
- **Goal**: Verify that local/dev can stay on mock data when the policy resolves to mock-only.
- **Steps**:
  1. Set `ENVIRONMENT=development`.
  2. Set `FORCE_GCP_REAL_DATA=false`.
  3. Ensure the frontend points to the local backend.
  4. Open `http://localhost:3000/dashboard`.
  5. Refresh the page and inspect the GCP Infrastructure Costs card.
- **Expected Outcome**:
  - The backend log shows policy resolution and mock-only mode.
  - The dashboard displays mock data.
  - `is_mock=true` in the response.

### Scenario 2: Local Explicit Real Override
- **Goal**: Verify that local/dev can still force real data when explicitly requested.
- **Steps**:
  1. Set `ENVIRONMENT=development`.
  2. Set `FORCE_GCP_REAL_DATA=true`.
  3. Ensure `GCP_PROJECT_ID` and `GCP_BILLING_BIGQUERY_DATASET` are configured.
  4. Refresh `http://localhost:3000/dashboard`.
- **Expected Outcome**:
  - The backend logs show real-data path selection.
  - The endpoint queries BigQuery.
  - `is_mock=false` when BigQuery data is returned.

### Scenario 3: Neon-Driven Policy
- **Goal**: Verify that Neon `system_config.gcp_force_real_data` can drive the result when local env does not force real data.
- **Steps**:
  1. Set `ENVIRONMENT=development`.
  2. Set `FORCE_GCP_REAL_DATA=false`.
  3. Set Neon `system_config.gcp_force_real_data=true`.
  4. Refresh `http://localhost:3000/dashboard`.
- **Expected Outcome**:
  - The backend logs show the Neon override being read.
  - The GCP billing route uses the Neon value.
  - The card shows real data if BigQuery credentials are valid.

### Scenario 4: Backend Fallback Safety
- **Goal**: Verify that the endpoint still fails safely when real data is requested but BigQuery config is missing or invalid.
- **Steps**:
  1. Set the policy to real-data mode.
  2. Remove or invalidate `GCP_PROJECT_ID` or `GCP_BILLING_BIGQUERY_DATASET`.
  3. Call `GET /api/v1/metrics/gcp-costs`.
- **Expected Outcome**:
  - The backend raises a clear error for missing config in real-data mode.
  - No silent false-positive real-data state is returned.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Backend Test Result**
  - `pytest backend/tests/test_gcp_billing.py -q`
  - Expected: `12 passed`
- **Log Snippet**
  ```text
  [GCP_BILLING] resolve_force_real_data(local) ...
  [GCP_BILLING] Neon override resolved ...
  [GCP_BILLING] get_current_month_costs ...
  ```
