# Manual Verification: Tak Radar Station Integration (tak / ดอยมูเซอ)

## 📋 Verification Overview
Verified the addition of the Tak (Doi Muser) radar station (`tak`) in FonMaYang backend configuration, catalog, test suite, and Admin frontend UI prefill.

---

## 🧪 Verification Steps & Automated Commands

### 1. Run Unit Tests (TDD Verification)
Execute the pytest suite for the Tak radar station and deployment environment synchronization:

```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/pytest tests/test_tak_radar.py -v
venv/bin/pytest tests/test_deploy_env_sync.py -v
```

**Expected Result:**
- All 3 tests in `test_tak_radar.py` pass:
  - `test_tak_station_registered`: PASSED
  - `test_tak_terrain_green_not_detected_as_rain`: PASSED
  - `test_tak_legitimate_rain_detected`: PASSED
- `test_deploy_env_sync.py` passes (100%).

---

### 2. Verify Station Preset API Endpoint
Run Python inline check against catalog preset loader:

```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/python3 -c "
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar_config import STATIONS

tak_station = STATIONS.get('tak')
print('STATIONS tak:', tak_station.code, tak_station.name, tak_station.center_lat, tak_station.center_lng)

tak_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p['code'] == 'tak'), None)
print('Catalog preset tak:', tak_preset['code'], tak_preset['name'])
"
```

**Expected Result:**
- Output displays `tak` details: `Doi Muser, Tak Province (240km) / ตาก (ดอยมูเซอ)` with `center_lat=16.7539` and `center_lng=98.9228`.

---

### 3. Frontend Admin UI Verification
1. Launch Frontend dev server if not running (`cd frontend && npm run dev`).
2. Navigate to `http://localhost:3000/admin/radar`.
3. Check the default form fields.

**Expected Result:**
- Station Code: `tak`
- Station Name: `Doi Muser, Tak Province (240km) / ตาก (ดอยมูเซอ)`
- Static Radar Image URL: `https://weather.tmd.go.th/tak/tak240_latest.jpg`
- Loop Page URL: `https://weather.tmd.go.th/takloop.php`
- Loop GIF URL: `https://weather.tmd.go.th/tak/takloop.gif`
- Center Lat / Lng: `16.7539` / `98.9228`
- Radius: `240 km`
