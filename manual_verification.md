# Manual Verification Plan - Cloud Run API Optimizations (Issues #278, #279, #280)

- **Branch**: `feat/278-optimize-backend-runway`
- **MR / Issue ID**: Issues #278, #279, #280
- **Date**: 2026-08-18

---

## 📌 Prerequisites & Environment Setup
1. Standard environment configuration.
2. Launch the backend server locally:
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Redundant Fetching & Short Transactions in `check_rain_and_alert`
- **Goal**: Verify that `check_rain_and_alert` executes quickly without calling `fetch_tmd_radar_routine` and keeps DB connection transactions extremely short.
- **Steps**:
  1. Trigger the check rain worker endpoint locally:
     ```bash
     curl -X POST http://localhost:8080/worker/check-rain -H "Authorization: Bearer my_super_secret_worker_key_123!"
     ```
  2. Monitor the backend logs.
- **Expected Outcome**:
  - The request should complete in less than 5 seconds (not 200s).
  - Logs should NOT output "Starting TMD Radar Cache Phase...".
  - Logs should show: "Starting proactive rain check..." and then complete recording metrics without connection closed warnings.

---

### Scenario 2: Server-Sent Events (SSE) Stream 30s Lifetime Limit
- **Goal**: Verify that `/api/v1/events/stream` automatically terminates the connection after 30 seconds to save Cloud Run billing costs.
- **Steps**:
  1. Make a request to the SSE endpoint using `curl` and track the duration:
     ```bash
     time curl -i http://localhost:8080/api/v1/events/stream
     ```
- **Expected Outcome**:
  - The response headers should return `text/event-stream`.
  - The connection should close automatically after exactly **30 seconds**.
  - The `time` command should output approximately `real 0m30.xxx s`.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Automated Verification Summary**:
  - `pytest` result: `4 passed` in `test_event_broadcaster.py`
  - `pytest` result: `17 passed` in `test_scheduler.py`
