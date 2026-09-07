# Manual Verification: File Logging & Growth/Decay Telemetry

## Overview
- Added rotating file logging (`backend/logs/backend.log`) with `SensitiveDataFilter`.
- Added structured telemetry logs `[GROWTH_DECAY]` and `[GROWTH_DECAY_CALC]` tracking storm cluster growth/decay rates and intensity trends over 15-minute intervals.
- Bumped project version to `0.73.2`.

---

## Prerequisites
- Backend service running locally on port 8000 or invoked via test suite.

---

## Verification Steps

### 1. Verify File Logging & Sensitive Data Masking
1. Send any request to the backend:
   ```bash
   curl -s http://localhost:8000/health
   ```
2. Check that `backend/logs/backend.log` exists and records the request:
   ```bash
   tail -n 10 backend/logs/backend.log
   ```
   **Expected Output:**
   Shows access logs and startup info formatted as:
   `YYYY-MM-DD HH:MM:SS,mmm [INFO] uvicorn.access: 127.0.0.1:... - "GET /health HTTP/1.1" 200`

### 2. Verify Growth/Decay Telemetry Logging
1. Run automated test for growth/decay logging:
   ```bash
   pytest backend/tests/test_file_logging_and_growth_logs.py -v
   ```
   **Expected Output:**
   Both tests pass:
   - `test_file_logging_handler_configuration PASSED`
   - `test_growth_decay_logging_in_weather_manager PASSED`

2. When predicting rain via `/check` or radar routines, verify log lines:
   ```bash
   grep -E "\[GROWTH_DECAY" backend/logs/backend.log
   ```
   **Expected Format:**
   `[GROWTH_DECAY] context=... target=A now=30.0dBZ prev=20.0dBZ rate=+50.0%/15min trend=intensifying`
