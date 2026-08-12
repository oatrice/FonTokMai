# Manual Verification Guide: Chumphon Radar Station (`cmp`) & Alias `d`

## Prerequisites
- Local Python backend environment set up with `venv/bin/python`.
- Local FastAPI server or unit test execution environment.

## 1. Automated Unit Tests

Run the Chumphon radar unit tests & alias tests:
```bash
cd "/Users/oatrice/Software Project/FonMaYang/backend"
venv/bin/pytest tests/test_chumphon_radar.py tests/test_webhook.py -v
```

**Expected Outcome:**
- `test_chumphon_station_registered`: PASSED
- `test_chumphon_terrain_green_not_detected_as_rain`: PASSED
- `test_chumphon_legitimate_rain_detected`: PASSED
- `test_handle_rain_command_default_alias_d`: PASSED

---

## 2. Command Alias `d` Verification

Send Telegram / LINE commands using alias `d`:
```
/rain_pro d
/rain d
/rain_pro default
```

**Expected Outcome:**
- System recognizes `d` as alias for `default` location (un-named primary location).
- Returns rain forecast and radar overlay for default location.
