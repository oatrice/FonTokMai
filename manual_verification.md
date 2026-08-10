# Manual Verification Plan - TMD Radar Auto-calibration Pipeline & Neon DB Migration

- **Branch**: `feat/99-tmd-radar-auto-calibration`
- **MR / Issue ID**: `Closes #99`
- **Date**: `2026-08-10`

---

## 📌 Prerequisites & Environment Setup
1. Ensure Python virtual environment dependencies are installed (`opencv-python`, `numpy`, `httpx`, `fastapi`).
2. Run backend server locally or execute standalone CLI script:
   ```bash
   cd backend
   .venv/bin/python scripts/calibrate_station_cli.py --help
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: CLI Auto-Calibration Tool Execution & Verification Image Export
- **Goal**: Verify that `calibrate_station_cli.py` downloads a radar static image, runs Hough Circle Detection, calculates crop parameters, prints `StationConfig` snippet to stdout, and exports verification image `--verify`.
- **Steps**:
  1. Execute CLI command:
     ```bash
     python3 backend/scripts/calibrate_station_cli.py \
       --code svp240 \
       --name "Bangkok Suvarnabhumi (240km)" \
       --url "https://weather.tmd.go.th/svp/svp240_latest.jpg" \
       --lat 13.6860 \
       --lng 100.7486 \
       --radius_km 240.0 \
       --verify \
       --output_image /tmp/svp240_calibration_verify.jpg
     ```
- **Expected Outcome**:
  - Console prints `Detected Radar Circle: center=(cx, cy), radius=r px`.
  - Console outputs valid `StationConfig` Python snippet.
  - File `/tmp/svp240_calibration_verify.jpg` is generated with cyan crop box overlay and green radar boundary circle.

---

### Scenario 2: Web Admin API Auto-Calibration & Preview (`POST /api/v1/admin/radar/preview`)
- **Goal**: Verify that the Web Admin API endpoint returns auto-calibrated crop values and base64 preview image.
- **Steps**:
  1. Send cURL request to `/api/v1/admin/radar/preview`:
     ```bash
     curl -X POST http://localhost:8000/api/v1/admin/radar/preview \
       -H "Content-Type: application/json" \
       -d '{
         "code": "svp240",
         "name": "Bangkok Suvarnabhumi (240km)",
         "image_url": "https://weather.tmd.go.th/svp/svp240_latest.jpg",
         "lat": 13.686,
         "lng": 100.7486,
         "radius_km": 240.0
       }'
     ```
- **Expected Outcome**:
  - HTTP Status: `200 OK`
  - Response contains `"circle_detected": true`, `"crop_info": {...}`, `"preview_image_base64": "data:image/jpeg;base64,..."`.

---

## 📸 Proof of Verification (Artifacts & Logs)

### 1. Automated Test Suite Execution (9 Passed)
```text
backend/tests/test_auto_calibration.py .....                             [ 41%]
backend/tests/test_ocr_service.py ...ss.s                                [100%]

========================= 9 passed, 3 skipped in 0.41s =========================
```

### 2. Live Telegram Bot & Ubon Radar (`ubn240`) Verification
- **6-Frame Sequence Accumulation**:
  ```text
  INFO:app.services.weather_manager:[ubn240] 🗃️ Firestore cache LOADED — 6 frames, source=static_cache, latest_ts=1786372200
  INFO:app.services.weather_manager:[FRAME_ID] station=ubn240, source=static_cache, n_frames=6 (last_ts=1786372200), timestamps=[1786365000, 1786365900, 1786366800, 1786371300, 1786372200]
  ```
- **Native Widescreen Aspect Ratio Preservation (`936 x 797`)**:
  ```text
  Latest loaded curr_frame shape for full radar: (797, 936, 3)
  Rendered full radar (radar_latest.png) HQ dimension: width=2808, height=2391 (Ratio: 1.174 Widescreen)
  ```
