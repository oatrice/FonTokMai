# Manual Verification Steps for Issue #52 & Issue #99

This document outlines manual testing steps for verifying the Auto-calibration CLI and Nationwide TMD Radar Station coverage.

## Prerequisites
Ensure Python environment with `opencv-python`, `numpy`, and `pytest` installed.

## 1. Verify Auto-Calibration CLI Tool (`#99`)

Run the auto-calibration CLI command on a radar station URL:

```bash
PYTHONPATH=backend python -m app.scripts.calibrate_station_cli \
  --code cmi240 \
  --name "Chiang Mai (240km)" \
  --url https://weather.tmd.go.th/cmi/cmi240_latest.jpg \
  --lat 18.77 \
  --lng 98.97 \
  --radius_km 240 \
  --verify \
  --output_image calibration_cmi240_verify.jpg
```

### Expected Outcome:
- Outputs a valid `StationConfig` code snippet to stdout.
- Generates `calibration_cmi240_verify.jpg` showing a green detected circle around the radar scope boundary.

---

## 2. Verify Nationwide TMD Radar Station Registry (`#52`)

Run automated test suite for nationwide coverage:

```bash
PYTHONPATH=backend pytest backend/tests/test_nationwide_radar.py
```

### Expected Outcome:
- 100% pass rate.
- Confirms stations `kkn120`, `kkn240`, `skn240`, `bkk240`, `ntp240`, `cmi240`, `phs240`, `ubn240`, `srt240`, `pkt240` are properly configured with bounding boxes.
