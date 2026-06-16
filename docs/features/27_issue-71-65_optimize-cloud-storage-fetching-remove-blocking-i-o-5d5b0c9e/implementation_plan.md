# Batch 1: Cost Efficiency & Billing Batching Strategy (Issues #71 & #65)

This plan covers the implementation details for optimizing cloud storage interactions and decoupling long-running background tasks to prevent Cloud Run CPU throttling.

## User Review Required

> [!IMPORTANT]
> **Issue #65 Architecture Choice:** The issue mentions both Google Cloud Tasks and Google Cloud Pub/Sub as options. 
> - **Google Cloud Tasks** is generally preferred for HTTP targets (like Cloud Run endpoints) because it allows easy configuration of rate limits, retries, and direct HTTP routing without needing an event-driven subscriber setup.
> - **Google Cloud Pub/Sub** is better for high-throughput, fan-out event-driven architectures.
> 
> **Proposed Path:** I recommend proceeding with **Google Cloud Tasks**. Please confirm if this is acceptable, or if you strictly prefer Pub/Sub.

> [!CAUTION]
> **GCP Project Configuration:** Using Cloud Tasks or Pub/Sub will require provisioning those resources (e.g., creating a Cloud Tasks Queue) in your GCP project. The application will also need the `google-cloud-tasks` Python package added to `requirements.txt`.

## Open Questions

1. **Cloud Tasks Queue Name & Location:** If we use Cloud Tasks, do you have an existing Queue name and GCP location we should use, or should we define environment variables (e.g., `GCP_PROJECT`, `GCP_LOCATION`, `CLOUD_TASKS_QUEUE`)?
2. **Webhook Worker:** For Telegram Webhooks that require long processing (like checking rain maps dynamically), should we also move them to a Cloud Task worker? (i.e. User sends a message -> API receives webhook -> enqueue task -> returns 200 OK -> Task worker processes and sends Telegram message back).

## Proposed Changes

---

### Radar Processor Optimization (Issue #71)

#### [MODIFY] `backend/app/services/weather_manager.py`
- Add an in-memory cache dictionary (`self.tmd_frames_cache`) in `WeatherManager.__init__()`.
- Update `_get_tmd_prediction()` to check this cache before calling `fetch_loop_gif_and_extract_frames()`. If cached frames for the `station_code` exist, use them directly, preventing N+1 Cloud Storage downloads within the same cron execution loop.

#### [MODIFY] `backend/app/services/tmd_radar_processor.py`
- Wrap all synchronous `google-cloud-storage` blocking calls with `asyncio.to_thread` to prevent event loop freezing.
  - `blob.download_as_bytes()` in `fetch_latest_image_bytes` and `fetch_loop_gif_and_extract_frames`.
  - `blob.upload_from_string()` in `save_polled_frame`.
  - `bucket.list_blobs()` and `blob.delete()` in `cleanup_old_frames`.

---

### Background Tasks Migration (Issue #65)

#### [NEW] `backend/app/services/cloud_tasks.py`
- Create a service wrapper for `google-cloud-tasks`.
- Expose methods to enqueue HTTP requests to internal worker endpoints (e.g., `enqueue_check_rain()`, `enqueue_webhook_process()`).

#### [MODIFY] `backend/requirements.txt`
- Add `google-cloud-tasks` (or `google-cloud-pubsub` based on feedback).

#### [NEW] `backend/app/routers/worker.py`
- Create a new router for internal worker endpoints that perform the heavy lifting.
  - `POST /worker/check-rain`
  - `POST /worker/check-disasters`
  - `POST /worker/process-webhook`
- These endpoints will execute the actual long-running functions (e.g., `check_rain_and_alert()`).

#### [MODIFY] `backend/app/routers/scheduler.py`
- Update existing cron endpoints (`/check-rain`, `/check-disasters-frequent`, etc.) to instantly enqueue a payload to Cloud Tasks and return a `200 OK` response.

#### [MODIFY] `backend/app/routers/webhook.py`
- Update the main `/webhook` endpoint to offload heavy Telegram commands to Cloud Tasks, allowing the webhook to return `200 OK` to Telegram within the 10-second timeout window.

## Verification Plan

### Automated Tests
- No new automated tests are specified, but we will ensure the Python app builds correctly and starts without syntax/import errors.

### Manual Verification
- Deploy the modified backend to a staging/development environment.
- Trigger the `/check-rain` scheduler endpoint and verify via logs that it returns `200 OK` instantly and enqueues a task.
- Verify in Cloud Run logs that the worker endpoint successfully executes the task and downloads the radar GIF only **once** per execution batch.
- Verify that `user_execution` latency metrics in GCP are significantly reduced.
