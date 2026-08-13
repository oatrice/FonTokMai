# Manual Verification - Chiang Rai (`cri`) TMD Radar Station

## Verification Overview
This document summarizes the steps taken to verify the integration of the **Chiang Rai 240km (`cri`)** radar station into the FonMaYang system.

---

## 1. Automated Test Execution (Pytest)

### Command
```bash
./backend/venv/bin/pytest backend/tests/test_chiang_rai_radar.py -v
```

### Result
```text
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0
rootdir: /Users/oatrice/Software Project/FonMaYang
plugins: anyio-4.14.0, mock-3.15.1, cov-7.1.0, asyncio-1.4.0, respx-0.23.1
collected 4 items

backend/tests/test_chiang_rai_radar.py::test_chiang_rai_station_registered PASSED [ 25%]
backend/tests/test_chiang_rai_radar.py::test_chiang_rai_pin_pixel_location PASSED [ 50%]
backend/tests/test_chiang_rai_radar.py::test_chiang_rai_terrain_green_not_detected_as_rain PASSED [ 75%]
backend/tests/test_chiang_rai_radar.py::test_chiang_rai_legitimate_rain_detected PASSED [100%]

========================= 4 passed, 1 warning in 1.39s =========================
```

---

## 2. Environment Variables & Sync Check

### Command
```bash
./backend/venv/bin/pytest backend/tests/test_deploy_env_sync.py
```

### Result
```text
============================= test session starts ==============================
collected 1 item

backend/tests/test_deploy_env_sync.py .                                  [100%]

============================== 1 passed in 0.02s ===============================
```

---

## 3. Key Parameters & Bounding Box Check

| Field | Config Value |
| :--- | :--- |
| **Station Code** | `cri` |
| **Name** | Chiang Rai (240km) / เชียงราย |
| **Center Lat / Lng** | `19.9609, 99.8824` |
| **Radius** | `240.0 km` |
| **Bounding Box** | `lat_max: 22.12, lng_min: 97.72, lat_min: 17.80, lng_max: 102.04` |
| **Static Image Crop** | `x=71, y=29, w=724, h=724` |
| **Loop Image Crop** | `x=71, y=29, w=724, h=724` |

---

## 4. Web Frontend Prefill Verification

- **Page Component**: [`frontend/src/app/admin/radar/page.tsx`](file:///Users/oatrice/Software%20Project/FonMaYang/frontend/src/app/admin/radar/page.tsx)
- **Coverage Map Component**: [`frontend/src/components/RadarCoverageMap.tsx`](file:///Users/oatrice/Software%20Project/FonMaYang/frontend/src/components/RadarCoverageMap.tsx)
- **Prefilled Form Initial State**:
  - `code`: `"cri"`
  - `name`: `"Chiang Rai (240km) / เชียงราย"`
  - `static_radar_image_url`: `"https://weather.tmd.go.th/cri/cri240_latest.jpg"`
  - `loop_page_url`: `"https://weather.tmd.go.th/criloop.php"`
  - `loop_gif_url`: `"https://weather.tmd.go.th/cri/criloop.gif"`
  - `center_lat`: `19.9609`
  - `center_lng`: `99.8824`
  - `radius_km`: `240.0`
- **Default Stations Map Dataset**: Added `cri` ("เชียงราย") preset under `"north"` region in `DEFAULT_STATIONS`.

