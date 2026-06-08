### Manual Verification Guide

Follow these steps to locally verify the Cloud Run Dashboard Metrics Export feature:

**Step 1: Start the Local Server**
1. Open a terminal and navigate to the `backend` directory.
2. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
*Expected Result:* The server starts successfully on `http://127.0.0.1:8000`.

**Step 2: Generate Sample Metrics Data**
1. We need to trigger the cron routines to populate the database with metrics.
2. If you have an endpoint to trigger it manually, run:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/cron/check-rain
   ```
   *(Alternatively, wait for the background scheduler to run `check_rain_and_alert` or `fetch_tmd_radar_routine` automatically if you have it running, or use a test script).*
*Expected Result:* The routine completes successfully and logs a metric entry into the local SQLite database.

**Step 3: Verify JSON Export (Unauthorized and Authorized)**
1. Try accessing without the secret header:
   ```bash
   curl -i -X GET http://127.0.0.1:8000/api/v1/metrics/export
   ```
   *Expected Result:* HTTP 401 Unauthorized.
2. Try accessing with the correct secret header:
   ```bash
   curl -X GET -H "X-Cron-Secret: default_secret_for_local_testing" "http://127.0.0.1:8000/api/v1/metrics/export?days=7"
   ```
*Expected Result:* HTTP 200 OK with a JSON payload aggregating the routines. For example:
```json
{
  "routines": {
    "check_rain": {
      "total_runs": 1,
      "avg_duration_s": 2.5,
      ...
    }
  },
  "period_days": 7,
  "generated_at": "..."
}
```

**Step 4: Verify CSV Export**
1. Request the CSV format using the secret header:
   ```bash
   curl -X GET -H "X-Cron-Secret: default_secret_for_local_testing" "http://127.0.0.1:8000/api/v1/metrics/export?format=csv" -o metrics.csv
   ```
*Expected Result:* A file named `metrics.csv` is downloaded. Open it to verify it contains the raw logs with columns like `routine_name`, `run_at`, `duration_s`, `alerts_sent`, `locations_checked`, `errors`, and `extra_data`.
