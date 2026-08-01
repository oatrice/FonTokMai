# Manual Verification Plan — GCP Infrastructure Costs Multi-Period Selector & Net Cost Calculation

- **Branch**: `feat/146-147-227-financial-dashboard`
- **MR / Issue ID**: `MR !78` / `Issue #211, #227`
- **Date**: `2026-08-01`

---

## 📌 Prerequisites & Environment Setup

1. **Environment Variables**:
   - `GCP_PROJECT_ID=fonmayang`
   - `GCP_BILLING_BIGQUERY_DATASET=fonmayang.gcp_billing_export`
   - `GOOGLE_APPLICATION_CREDENTIALS=/Users/oatrice/.config/gcloud/application_default_credentials.json`
   - `CRON_SECRET=CRON_SECRET`

2. **Launch Backend Server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

3. **Launch Frontend Dev Server**:
   ```bash
   npm run dev --prefix frontend
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Fetch Current Month Costs (Net Cost Deduction & THB Currency)
- **Goal**: Verify Backend calculates Net Cost (costs - credits) in THB natively for `current_month`.
- **Steps**:
  ```bash
  curl -s -H "x-cron-secret: CRON_SECRET" "http://localhost:8000/api/v1/metrics/gcp-costs?period=current_month"
  ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body: Returns `currency: "THB"`, `is_mock: false`, and `total_thb`.

---

### Scenario 2: Fetch Last Month Costs with `invoice.month` Filter
- **Goal**: Verify `period=last_month` uses BigQuery `invoice.month` matching GCP Console Invoice reports 100%.
- **Steps**:
  ```bash
  curl -s -H "x-cron-secret: CRON_SECRET" "http://localhost:8000/api/v1/metrics/gcp-costs?period=last_month"
  ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body: `{"cloud_run_thb": 66.6, "cloud_storage_thb": 0.58, "egress_thb": 0, "other_thb": 7.53, "total_thb": 74.71, "currency": "THB", "is_mock": false}`

---

### Scenario 3: UI Period Dropdown Interaction & Skeleton Loader
- **Goal**: Verify changing period in `GCPCostBreakdown` component re-fetches costs and displays skeleton loading state without rendering mock defaults.
- **Steps**:
  1. Open `http://localhost:3000/dashboard`.
  2. Locate **GCP Infrastructure Costs** card.
  3. Select **"Last Month"** or **"Last 30 Days"** from the glass period selector dropdown.
- **Expected Outcome**:
  - Card displays animated pulse skeleton loader briefly during fetch.
  - Updates total THB and period date range without showing amber "Mock Data" badge.

---

## 📸 Proof of Verification (Artifacts & Logs)

### Automated Unit Test Summary
- **Backend Pytest (`backend/tests/test_gcp_billing.py`)**: `8 passed` (100%)
- **Frontend Jest (`frontend/src/__tests__/FinancialDashboard.test.tsx`)**: `5 passed` (100%)

```text
PASS backend/tests/test_gcp_billing.py (8/8 tests passed)
PASS frontend/src/__tests__/FinancialDashboard.test.tsx (5/5 tests passed)
```

### Direct BigQuery Verification Query Output
```text
+---------------------+--------------------+---------------+-------------------+
| service_description |     usage_cost     | total_credits |     net_cost      |
+---------------------+--------------------+---------------+-------------------+
| Cloud Run           | 139.06598299999996 |   -72.470214  | 66.59576899999999 |
| Cloud Scheduler     |            4.30264 |          0.0  |           4.30264 |
| Artifact Registry   |  3.225143999999999 |          0.0  | 3.225143999999999 |
| Cloud Storage       | 0.5822330000000001 |          0.0  | 0.5822330000000001|
+---------------------+--------------------+---------------+-------------------+
Total Net Cost: 74.71 THB (Matches BigQuery Export records from 2026-07-23 to 2026-07-31)
```
