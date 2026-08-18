# Manual Verification Plan - Cloud Run API Optimizations & Worker Shutdown (Issues #278, #279, #280, #281)

- **Branch**: `feat/278-optimize-backend-runway`
- **MR / Issue ID**: Issues #278, #279, #280, #281
- **Version**: `0.73.1`
- **Date**: 2026-08-18

---

## 📌 Prerequisites & Environment Setup
1. **Environment Setup:**
   - PostgreSQL (Neon DB) or SQLite database connected.
   - Python virtualenv activated (`backend/.venv/bin/activate`).
2. **Backend Server Launch:**
   - Run the local FastAPI backend server:
     ```bash
     uvicorn app.main:app --reload --port 8000
     ```

---

## 🧪 Verification Scenarios

### Scenario 1: Redundant Fetching & Short Transactions in `check_rain_and_alert`
- **Goal**: Verify that `check_rain_and_alert` executes quickly without calling `fetch_tmd_radar_routine` and keeps DB connection transactions extremely short.
- **Steps**:
  1. Trigger the check rain worker endpoint locally:
     ```bash
     curl -i -X POST http://localhost:8000/worker/check-rain \
       -H "X-Worker-Secret: default_secret_for_local_testing"
     ```
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
     time curl -i http://localhost:8000/api/v1/events/stream
     ```
- **Expected Outcome**:
  - The response headers should return `text/event-stream`.
  - The connection should close automatically after exactly **30 seconds**.
  - The `time` command should output approximately `real 0m30.xxx s`.

---

### Scenario 3: Worker Endpoints Blocked on Emergency Shutdown (Shutdown Active)
- **Goal**: Verify that all background scheduler worker endpoints (e.g. `/worker/check-rain`) instantly reject requests with `503 Service Unavailable` when the project's budget is exceeded (`emergency_shutdown` is set to `True` in system settings).
- **Steps**:
  1. Trigger the GCP Budget Alert webhook simulated payload representing a 100%+ budget violation:
     ```bash
     curl -X POST http://localhost:8000/api/v1/internal/budget-alert \
       -H "Content-Type: application/json" \
       -d '{
         "message": {
           "data": "eyJidWRnZXREaXNwbGF5TmFtZSI6ICJmb25tYXlhbmctbW9udGhseS1idWRnZXQiLCAiYWxlcnRUaHJlc2hvbGRFeGNlZWRlZCI6IDEuMCwgImNvc3RBbW91bnQiOiA2Mi44NiwgImJ1ZGdldEFtb3VudCI6IDUwLjB9"
         }
       }'
     ```
  2. Send a POST request to a worker cron endpoint (e.g., `/worker/check-rain`):
     ```bash
     curl -i -X POST http://localhost:8000/worker/check-rain \
       -H "X-Worker-Secret: default_secret_for_local_testing"
     ```
- **Expected Outcome**:
  - The budget alert webhook returns success, and logs confirm that `emergency_shutdown = True` has been written to the database.
  - The request to `/worker/check-rain` returns **`HTTP/1.1 503 Service Unavailable`** with:
    ```json
    {"detail": "Service suspended due to budget limit exceeded"}
    ```

---

### Scenario 4: Restore Command Unblocks Worker Endpoints (Restore)
- **Goal**: Verify that restoring public access clears the emergency shutdown flag and unblocks worker endpoints.
- **Steps**:
  1. Simulate the Telegram admin command `/restore_public_access` by POSTing to the task route:
     ```bash
     curl -i -X POST http://localhost:8000/worker/handle-restore-public-access \
       -H "X-Worker-Secret: default_secret_for_local_testing" \
       -H "Content-Type: application/json" \
       -d '{
         "chat_id": 12345,
         "command": "/restore_public_access",
         "username": "admin_user"
       }'
     ```
  2. Re-trigger the worker cron endpoint:
     ```bash
     curl -i -X POST http://localhost:8000/worker/check-rain \
       -H "X-Worker-Secret: default_secret_for_local_testing"
     ```
- **Expected Outcome**:
  - `/worker/handle-restore-public-access` returns **`200 OK`** (not blocked by the 503 check).
  - The subsequent request to `/worker/check-rain` goes through successfully, returning **`200 OK`** (or triggering rain forecasting logic normally) since `emergency_shutdown` has been reset to `False`.

---

## 📸 Proof of Verification (Automated Test Summary)
- **Automated Verification Summary**:
  - `pytest` test suite:
    - `test_event_broadcaster.py`: `3 passed`
    - `test_scheduler.py`: `16 passed`
    - `test_worker_shutdown.py`: `3 passed`

