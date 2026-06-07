# Tasks

- `[x]` 1. **Firestore Repository Updates**
  - `[x]` Add `get_latest_radar_cache` to `LocationRepository` protocol and `FirestoreLocationRepository`.
  - `[x]` Add `set_latest_radar_cache` to save Storage URLs and timestamps to `radar_latest_cache` collection.
- `[/]` 2. **Scheduler Task Updates**
  - `[ ]` Refactor `fetch_tmd_radar_routine` into a `cache_radar_routine` that runs OCR and saves to `radar_latest_cache` via Firestore.
  - `[ ]` Modify `check_rain_and_alert` to execute `cache_radar_routine` at the start.
- `[ ]` 3. **TMD Radar Processor Updates**
  - `[ ]` Update `TMDRadarProcessor.fetch_latest_image_bytes` to read from Firestore cache.
  - `[ ]` Update `TMDRadarProcessor.fetch_loop_gif_and_extract_frames` to read from Firestore cache.
- `[ ]` 4. **Verification**
  - `[ ]` Test via `/api/v1/cron/check-rain` to ensure pipeline works end-to-end.
