# Batch 1: Cost Efficiency & Billing Batching Strategy (Issues #71 & #65)

This plan covers the implementation details for optimizing cloud storage interactions and decoupling long-running background tasks to prevent Cloud Run CPU throttling, along with security and resilience mitigations.

## User Review Required

> [!IMPORTANT]
> **Issue #65 Architecture Choice:** The issue mentions both Google Cloud Tasks and Google Cloud Pub/Sub as options. 
> - **Google Cloud Tasks** is generally preferred for HTTP targets (like Cloud Run endpoints) because it allows easy configuration of rate limits, retries, and direct HTTP routing without needing an event-driven subscriber setup.
> - **Google Cloud Pub/Sub** is better for high-throughput, fan-out event-driven architectures.
> 
> **Decision:** Proceeded with **Google Cloud Tasks**.

> [!CAUTION]
> **OIDC vs API Secret สำหรับ Worker Auth**
> - **Decision:** Proceeded with **API Secret Header** (`X-Worker-Secret`) for easier Local Development without needing OIDC Emulator.

## Proposed Changes

---

### Radar Processor Optimization (Issue #71)

#### [MODIFY] `backend/app/services/weather_manager.py`
- Add an in-memory cache dictionary (`self.tmd_frames_cache`) in `WeatherManager.__init__()`.
- Update `_get_tmd_prediction()` to check this cache before calling `fetch_loop_gif_and_extract_frames()`.

#### [MODIFY] `backend/app/services/tmd_radar_processor.py`
- Wrap all synchronous `google-cloud-storage` blocking calls with `asyncio.to_thread` to prevent event loop freezing.

---

### Background Tasks Migration (Issue #65)

#### [NEW] `backend/app/services/cloud_tasks.py`
- Create a service wrapper for `google-cloud-tasks` and inject `X-Worker-Secret`.

#### [MODIFY] `backend/requirements.txt`
- Add `google-cloud-tasks`.

#### [NEW] `backend/app/routers/worker.py`
- Create a new router for internal worker endpoints.
- Secure endpoints with `X-Worker-Secret` dependency.
- Wrap all logic in `try...except` to return `HTTP 200 OK` on errors to prevent Cloud Tasks Retry Storms.

#### [MODIFY] `backend/app/routers/scheduler.py`
- Update existing cron endpoints to enqueue tasks.

#### [MODIFY] `backend/app/routers/webhook.py`
- Update the main `/webhook` endpoint to offload heavy Telegram commands to Cloud Tasks.

## Verification Plan

### Automated Tests
- Ensure the Python app builds correctly using `py_compile`.

### Manual Verification
- Refer to `manual_verification.md` for steps to verify caching, worker routing, security, and retry prevention.
