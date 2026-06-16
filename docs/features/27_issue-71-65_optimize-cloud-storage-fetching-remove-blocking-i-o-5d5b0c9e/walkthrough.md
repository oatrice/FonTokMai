# Walkthrough: Background Tasks Migration (Batch 1 - Issue #65)

I've completed the implementation for migrating inline processing to Google Cloud Tasks. This will prevent Cloud Run from throttling the CPU while processing long-running cron jobs and heavy Telegram commands, and ensures Webhooks return 200 OK well within Telegram's timeout limit.

## What was done

### 1. `CloudTasksService` Added
- **File**: [cloud_tasks.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/services/cloud_tasks.py)
- **Details**: Created a dedicated service leveraging `google-cloud-tasks` (v2.16.2) to enqueue tasks securely. It targets endpoints under the `WORKER_BASE_URL` provided in the `.env` file. If the `WORKER_BASE_URL` or `CLOUD_TASKS_QUEUE` isn't configured, it gracefully falls back to inline `background_tasks`.

### 2. Worker Endpoints
- **File**: [worker.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/routers/worker.py)
- **Details**: Created a new `/worker` router containing API endpoints that will act as targets for Cloud Tasks:
  - `/worker/check-rain`
  - `/worker/check-disasters-frequent`
  - `/worker/check-disasters-infrequent`
  - `/worker/fetch-tmd-radar`
  - `/worker/trigger-mock-disaster`
  - `/worker/process-telegram-location`
  - `/worker/handle-mylocation`
  - `/worker/handle-radar`
  - `/worker/handle-rain`
  - `/worker/handle-devmock`
- Registered the `worker.router` in [main.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/main.py).

### 3. Refactored `scheduler.py`
- **File**: [scheduler.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/routers/scheduler.py)
- **Details**: Updated all external cron triggers to enqueue tasks using `CloudTasksService` instead of directly `await`-ing routines or using `BackgroundTasks`.

### 4. Refactored `webhook.py`
- **File**: [webhook.py](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/routers/webhook.py)
- **Details**: Updated the main Telegram webhook logic. Whenever a location or a heavy command (`/rain`, `/radar`, `/devmock`, etc.) is received, it enqueues the payload to a worker endpoint and returns `200 OK` to Telegram immediately. A "กำลังประมวลผล..." (loading state) message is sent immediately for locations, and the worker will update it later.

## Verification
- Added `google-cloud-tasks==2.16.2` to `requirements.txt`.
- Executed `python3 -m py_compile` across all modified files to ensure zero syntax errors.

> [!TIP]
> **Deployment Steps**
> 1. Make sure to set `WORKER_BASE_URL` in your production environment (e.g., your Cloud Run service URL).
> 2. Ensure your Cloud Run service account has permissions to enqueue to Google Cloud Tasks (`roles/cloudtasks.enqueuer`).
> 3. Verify that the Cloud Tasks Queue (`webhook-worker-queue`) exists in your target GCP project.
