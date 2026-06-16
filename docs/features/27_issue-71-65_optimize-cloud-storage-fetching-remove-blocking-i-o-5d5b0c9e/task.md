# Task: Batch 1 Implementation (Issues #71 & #65)

## Issue #71: Radar Processor Cloud Storage Optimization
- `[x]` Update `WeatherManager` to include `tmd_frames_cache`.
- `[x]` Update `WeatherManager._get_tmd_prediction` to check and set the cache.
- `[x]` Update `TMDRadarProcessor.fetch_latest_image_bytes` to use `asyncio.to_thread`.
- `[x]` Update `TMDRadarProcessor.fetch_loop_gif_and_extract_frames` to use `asyncio.to_thread`.
- `[x]` Update `TMDRadarProcessor.save_polled_frame` to use `asyncio.to_thread`.
- `[x]` Update `TMDRadarProcessor.cleanup_old_frames` to use `asyncio.to_thread`.

## Issue #65: Background Tasks Migration (Google Cloud Tasks)
- `[x]` Add `google-cloud-tasks` to `requirements.txt`.
- `[x]` Create `app/services/cloud_tasks.py`.
- `[x]` Create `app/routers/worker.py`.
- `[x]` Refactor `scheduler.py` endpoints to enqueue tasks.
- `[x]` Refactor `webhook.py` endpoints to enqueue tasks.

## Worker Security & Mitigation (Issue #65 follow-up)
- `[x]` Add `X-Worker-Secret` dependency to `worker.py` router.
- `[x]` Update `cloud_tasks.py` to send `X-Worker-Secret` header.
- `[x]` Wrap worker endpoints in `try...except` to return `HTTP 200` with an error body on external API failures (prevent Retry Storms).
- `[x]` Verify idempotency behavior in webhook tasks.

## Verification
- `[x]` Ensure code runs without syntax errors using `py_compile`.
