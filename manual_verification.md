# Manual Verification Guide: Chumphon Radar Station (`cmp`)

## Prerequisites
- Local Python backend environment set up with `venv/bin/python`.
- Local FastAPI server or unit test execution environment.

## 1. Automated Unit Tests

Run the Chumphon radar unit tests:
```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/pytest tests/test_chumphon_radar.py -v
```

**Expected Outcome:**
- `test_chumphon_station_registered`: PASSED
- `test_chumphon_terrain_green_not_detected_as_rain`: PASSED
- `test_chumphon_legitimate_rain_detected`: PASSED

---

## 2. Admin API Preview Verification

Send a preview request to verify image cropping & rendering for Chumphon station:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/radar/preview" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "cmp",
    "name": "Chumphon (240km) / ชุมพร",
    "image_url": "https://weather.tmd.go.th/cmp/cmp240_latest.jpg",
    "loop_gif_url": "https://weather.tmd.go.th/cmp/cmpLoop.gif",
    "lat": 10.4931,
    "lng": 99.1800,
    "radius_km": 240.0
  }'
```

**Expected Outcome:**
- HTTP status 200 OK
- Returns JSON with cropped image preview & detected center deviation.

---

## 3. Bot Command Integration Verification

Run the radar bot test CLI or send a Telegram command to the local dev bot:
```
/rain_pro cmp
```

**Expected Outcome:**
- Bot fetches latest Chumphon radar scan (`cmp240_latest.jpg` or `cmpLoop.gif`).
- Correctly renders rain overlay and trajectory predictions.
