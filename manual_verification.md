# Manual Verification Document: Surat Thani (`srt`) TMD Radar Station Integration

**Date**: 2026-08-13  
**Version**: `v0.72.28`  
**Station Code**: `srt`  
**Station Name**: Surat Thani (240km) / สุราษฎร์ธานี  

---

## 🎯 Scope of Changes
- Integrated Surat Thani TMD Radar station (`srt`) with center coordinates `(9.1333, 99.3333)` and radius `240.0 km`.
- Configured bounding box `SRT240_BBOX` (`lat_max=11.29, lng_min=97.17, lat_min=6.97, lng_max=101.49`) in [`tmd_radar_config.py`](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/services/tmd_radar_config.py) and [`tmd_radar_catalog.py`](file:///Users/oatrice/Software%20Project/FonMaYang/backend/app/services/tmd_radar_catalog.py).
- Created TDD unit test suite [`backend/tests/test_surat_thani_radar.py`](file:///Users/oatrice/Software%20Project/FonMaYang/backend/tests/test_surat_thani_radar.py).
- Prefilled Web Admin Frontend form state in [`frontend/src/app/admin/radar/page.tsx`](file:///Users/oatrice/Software%20Project/FonMaYang/frontend/src/app/admin/radar/page.tsx).
- Updated [`RadarCoverageMap.tsx`](file:///Users/oatrice/Software%20Project/FonMaYang/frontend/src/components/RadarCoverageMap.tsx) preset station list (`"srt"`, region: `"south"`).

---

## 🧪 Verification Commands & Test Results

### 1. Pytest Verification
Executed automated test commands:
```bash
./backend/venv/bin/pytest backend/tests/test_surat_thani_radar.py backend/tests/test_nationwide_radar.py backend/tests/test_deploy_env_sync.py -v
```

#### Output:
```text
============================= test session starts ==============================
platform darwin -- Python 3.14.6, pytest-9.1.0, pluggy-1.6.0
rootdir: /Users/oatrice/Software Project/FonMaYang
collected 9 items

backend/tests/test_surat_thani_radar.py :: test_surat_thani_station_registered PASSED
backend/tests/test_surat_thani_radar.py :: test_surat_thani_pin_pixel_location PASSED
backend/tests/test_surat_thani_radar.py :: test_surat_thani_maritime_and_terrain_colors_not_detected_as_rain PASSED
backend/tests/test_surat_thani_radar.py :: test_surat_thani_legitimate_rain_detected PASSED
backend/tests/test_nationwide_radar.py :: test_nationwide_stations_present PASSED
backend/tests/test_nationwide_radar.py :: test_chainat_preset_in_catalog PASSED
backend/tests/test_nationwide_radar.py :: test_phitsanulok_preset_in_catalog PASSED
backend/tests/test_nationwide_radar.py :: test_chumphon_preset_in_catalog PASSED
backend/tests/test_deploy_env_sync.py :: test_deploy_env_sync PASSED

========================= 9 passed in 1.68s =========================
```

---

## 📋 Checklist
- [x] TDD Red-Green-Refactor cycle verified for `srt` radar station
- [x] Sea/maritime and terrain background colors correctly ignored (0 dBZ)
- [x] Admin frontend default form state and coverage map presets updated
- [x] Version synced across `VERSION`, `backend/VERSION`, `frontend/package.json`, and `CHANGELOG.md` (`0.72.28`)
