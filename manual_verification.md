# Manual Verification Document — Phitsanulok (`phs`) TMD Radar Station Integration

## 📌 Feature Overview
This verification document covers the onboarding and integration of the **Phitsanulok (`phs`) TMD Radar Station (240km radius)** into the FonMaYang weather tracking platform (v0.72.15).

- **Station Code**: `phs`
- **Name**: `Phitsanulok (240km) / พิษณุโลก`
- **Static Image URL**: `https://weather.tmd.go.th/phs/phs240_latest.jpg`
- **Loop Page URL**: `https://weather.tmd.go.th/phsloop.php`
- **Loop GIF URL**: `https://weather.tmd.go.th/phs/phsloop.gif`
- **Center Coordinates**: Lat `16.7828`, Lng `100.2786`
- **Radius**: `240.0` km

---

## 🛠️ Prerequisites
1. Backend environment running with virtualenv at `backend/venv/`.
2. Access to Web Admin Portal (`frontend/src/app/admin/radar/page.tsx`).
3. Neon Postgres DB connection for station preset persistence.

---

## 🧪 Automated Verification Results

### 1. Phitsanulok Station Unit & Terrain Rejection Tests
```bash
backend/venv/lib/pytest backend/tests/test_phitsanulok_radar.py
```
**Outcome:** ✅ `3 passed in 1.82s`
- `test_phitsanulok_station_registered`: Verified station config registration and catalog preset.
- `test_phitsanulok_terrain_green_not_detected_as_rain`: Verified mountain/ground background colors are rejected (0.0 dBZ).
- `test_phitsanulok_legitimate_rain_detected`: Verified legitimate rain green/yellow colors are detected (>= 20.0 dBZ).

### 2. Nationwide Station Registry & Admin Router Verification
```bash
backend/venv/lib/pytest backend/tests/test_nationwide_radar.py backend/tests/test_admin_radar_router.py
```
**Outcome:** ✅ `6 passed in 2.01s`
- `test_nationwide_stations_present`: Verified `phs` and `phs240` presence in station registry.
- `test_phitsanulok_preset_in_catalog`: Verified catalog preset presence and lat/lng values.
- `test_preview_endpoint` & `test_save_and_list_stations_endpoints`: Verified admin radar endpoints.

### 3. Deploy Environment Sync Check
```bash
backend/venv/lib/pytest backend/tests/test_deploy_env_sync.py
```
**Outcome:** ✅ `1 passed in 0.03s`

---

## 🔍 Manual Testing Steps

### Step 1: Web Admin Preset Prefill Verification
1. Navigate to `/admin/radar` on the Web Admin UI.
2. Verify that the initial form state defaults to **Phitsanulok (`phs`)** station parameters:
   - Code: `phs`
   - Name: `Phitsanulok (240km) / พิษณุโลก`
   - Static Radar Image URL: `https://weather.tmd.go.th/phs/phs240_latest.jpg`
   - Loop Page URL: `https://weather.tmd.go.th/phsloop.php`
   - Loop GIF URL: `https://weather.tmd.go.th/phs/phsloop.gif`
   - Lat: `16.7828`, Lng: `100.2786`, Radius: `240.0`
3. Select "Phitsanulok (240km) / พิษณุโลก" from the quick-select preset dropdown.
4. Click **Preview & Auto-Detect**. Verify the radar circle crop and bounding box calculation.

### Step 2: Station DB Seeding & Admin API Verification
1. Click **Submit to Neon DB** or trigger `/api/v1/admin/radar/seed`.
2. Verify response `200 OK` confirming `phs` station upserted into `radar_stations` table.
3. Verify station appears in `GET /api/v1/admin/radar/stations`.

### Step 3: Rain Alerting & Command Verification
1. Execute `/rain_pro phs` on Telegram/LINE bot interface.
2. Confirm the radar image crop is centered over Phitsanulok, neon contours align correctly, and ground terrain clutter is suppressed.
