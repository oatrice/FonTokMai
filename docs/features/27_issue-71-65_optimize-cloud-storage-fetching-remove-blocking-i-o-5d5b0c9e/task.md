# Task: Batch 1 Implementation (Issues #71 & #65)

- `[/]` Issue #71: Radar Processor Cloud Storage Optimization
  - `[ ]` Update `WeatherManager` to include `tmd_frames_cache`.
- `[x]` Issue #71: Radar Processor Cloud Storage Optimization
  - `[x]` Update `WeatherManager` to include `tmd_frames_cache`.
  - `[x]` Update `WeatherManager._get_tmd_prediction` to check and set the cache.
  - `[x]` Update `TMDRadarProcessor.fetch_latest_image_bytes` to use `asyncio.to_thread`.
  - `[x]` Update `TMDRadarProcessor.fetch_loop_gif_and_extract_frames` to use `asyncio.to_thread`.
  - `[x]` Update `TMDRadarProcessor.save_polled_frame` to use `asyncio.to_thread`.
  - `[x]` Update `TMDRadarProcessor.cleanup_old_frames` to use `asyncio.to_thread`.
- `[x]` Issue #65: Background Tasks Migration (Google Cloud Tasks)
  - `[x]` Add `google-cloud-tasks` to `requirements.txt`.
  - `[x]` Create `app/services/cloud_tasks.py`.
  - `[x]` Create `app/routers/worker.py`.
  - `[x]` Refactor `scheduler.py` endpoints to enqueue tasks.
  - `[x]` Refactor `webhook.py` endpoints to enqueue tasks.
- `[x]` Verification
  - `[x]` Ensure code runs without syntax errors.
