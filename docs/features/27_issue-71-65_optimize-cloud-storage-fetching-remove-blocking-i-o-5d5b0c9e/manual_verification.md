### Manual Verification Guide

**Objective**: Verify that the radar caching, GCS asynchronous wrapper, and Cloud Tasks background workers execute properly without blocking the event loop or causing syntax/runtime errors.

- **Step 1: Start the Local Environment**
  - Run the FastAPI application locally: `uvicorn app.main:app --reload --port 8000`
  - *Note*: You may need to set `WORKER_BASE_URL=http://localhost:8000` and export your `GCP_PROJECT`, `GCP_LOCATION`, and `CLOUD_TASKS_QUEUE` for Cloud Tasks routing. If you don't have a Cloud Tasks queue, the fallback logic will execute tasks inline (`BackgroundTasks`), which is also fine for verifying functionality.

- **Step 2: Verify Radar Processor Caching & Async I/O (Issue #71)**
  - Open Postman or use `curl` to trigger the webhook simulating a location update:
    ```bash
    curl -X POST http://localhost:8000/api/v1/telegram/webhook \
         -H "Content-Type: application/json" \
         -d '{"message": {"chat": {"id": 12345}, "location": {"latitude": 13.75, "longitude": 100.5}}}'
    ```
  - **Expected Result**: The webhook immediately returns `{"status": "ok"}`. In the terminal logs, you should see the radar processor running (`asyncio.to_thread`) without freezing the server. Check logs to see if caching is hit for subsequent identical requests.

- **Step 3: Verify Webhook Offloading to Worker (Issue #65)**
  - Send a heavy `/rain` or `/radar` command via webhook endpoint:
    ```bash
    curl -X POST http://localhost:8000/api/v1/telegram/webhook \
         -H "Content-Type: application/json" \
         -d '{"message": {"chat": {"id": 12345}, "text": "/rain"}}'
    ```
  - **Expected Result**: The webhook should instantly return `{"status": "ok"}`. In the logs, you should see `CloudTasksService` attempting to enqueue a task to `/worker/handle-rain`. If Cloud Tasks is not configured, it will fall back to executing `handle_rain_command` inline. You should see logs indicating the worker or background task started.

- **Step 4: Verify Scheduler Enqueue to Worker (Issue #65)**
  - Hit the scheduler endpoint using curl with the correct cron secret (replace `default_secret_for_local_testing` if configured otherwise):
    ```bash
    curl -X POST http://localhost:8000/api/v1/cron/check-rain \
         -H "X-Cron-Secret: default_secret_for_local_testing"
    ```
  - **Expected Result**: It returns `{"status": "ok", "message": "Rain check task enqueued"}` instantly. The logs should reflect that the worker endpoint `/worker/check-rain` was hit (via Cloud Tasks) or the background task started.

- **Step 5: Verify the Worker Endpoints**
  - Hit the worker endpoint directly to simulate Cloud Tasks hitting it:
    ```bash
    curl -X POST http://localhost:8000/worker/check-rain \
         -H "Content-Type: application/json" \
         -d '{}'
    ```
  - **Expected Result**: The worker runs `check_rain_and_alert()` and returns `{"status": "ok"}` upon completion.
