# Manual Verification Plan - TMD Radar Dynamic Station Integration & Calibration (Hat Yai `hyi`)

- **Branch**: `feat/99-tmd-radar-auto-calibration`
- **MR / Issue ID**: `Issue #99`, `Issue #273`
- **Version**: `0.72.0`
- **Date**: `2026-08-14`

---

## 📌 Prerequisites & Environment Setup
1. **Environment Setup:**
   - PostgreSQL (Neon DB) or SQLite database connected.
   - Python virtualenv activated (`backend/.venv/bin/activate`).
2. **Backend Server Launch:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
3. **Database Seed Sync (Required for new radar configurations):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/radar/seed
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Seed & Sync Dynamic Radar Stations into Database (Happy Path)
- **Goal**: Verify that all 13 validated TMD radar stations (including Hat Yai `hyi`, Surat Thani `srt`, and Chiang Rai `cri`) are seeded into Neon DB with their respective crop offsets and projection settings.
- **Steps**:
  1. Trigger the seed endpoint:
     ```bash
     curl -X POST http://localhost:8000/api/v1/admin/radar/seed
     ```
  2. Query active stations:
     ```bash
     curl -X GET http://localhost:8000/api/v1/admin/radar/stations
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response Body contains `{"status": "ok", "message": "Successfully synced DB to 13 validated radar stations."}`
  - Station list contains `hyi` with `projection_type: "linear"`, `static_crop_x: 55`, `static_crop_y: 34`, `static_crop_width: 720`, `static_crop_height: 720`.

---

### Scenario 2: Hat Yai Radar Pin Location & Rainfall Prediction (Happy Path)
- **Goal**: Verify that user coordinates in the Hat Yai area accurately map to pixel coordinates on the radar image without offset drift.
- **Steps**:
  1. In Telegram bot (or Webhook Dev Mock), send:
     ```text
     /rain_pro_d tmd radar
     ```
  2. Inspect generated `radar_latest.png` and `radar_tracking.jpg`.
- **Expected Outcome**:
  - Center of Radar crosshair aligns with center circle at `(640, 638)`.
  - User default location crosshair maps to `(857, 738)`.
  - Image generation returns valid rain tracking vectors without out-of-bounds clipping.

---

### Scenario 3: Marine & Terrain Green False-Positive Filtering (Edge Case)
- **Goal**: Verify that sea background (Gulf of Thailand / Andaman Sea) and mountainous terrain colors in Hat Yai scans are ignored and do not trigger false rain alerts.
- **Steps**:
  1. Run automated color extractor test:
     ```bash
     backend/.venv/bin/pytest backend/tests/test_hat_yai_radar.py -k "test_hat_yai_maritime_and_terrain_colors_not_detected_as_rain"
     ```
- **Expected Outcome**:
  - Test passes: all terrain greens and maritime blues resolve to `0.0 dBZ`.

---

## 📸 Proof of Verification (Automated Test & Build Logs)

### 1. Backend Radar Unit Test Suite
```text
============================= test session starts ==============================
backend/tests/test_admin_radar_router.py::test_preview_endpoint PASSED   [ 16%]
backend/tests/test_admin_radar_router.py::test_save_and_list_stations_endpoints PASSED [ 33%]
backend/tests/test_hat_yai_radar.py::test_hat_yai_station_registered PASSED [ 50%]
backend/tests/test_hat_yai_radar.py::test_hat_yai_pin_pixel_location PASSED [ 66%]
backend/tests/test_hat_yai_radar.py::test_hat_yai_maritime_and_terrain_colors_not_detected_as_rain PASSED [ 83%]
backend/tests/test_hat_yai_radar.py::test_hat_yai_legitimate_rain_detected PASSED [100%]
backend/tests/test_surat_thani_radar.py .... PASSED
backend/tests/test_chiang_rai_radar.py .... PASSED
backend/tests/test_tak_radar.py .... PASSED
backend/tests/test_deploy_env_sync.py . PASSED
========================= 20 passed in 3.42s =========================
```

### 2. Frontend Production Build Verification
```text
▲ Next.js 16.2.11 (Turbopack)
- Environments: .env
✓ Compiled successfully in 6.1s
✓ Generating static pages using 9 workers (9/9) in 471ms
Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /admin/radar
├ ƒ /api/metrics/gcp-costs
├ ƒ /api/milestones
├ ƒ /api/runway
└ ○ /dashboard
○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```
