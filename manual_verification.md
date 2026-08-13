# Manual Verification: Hat Yai Radar Station (`hyi`) Integration

## 📌 Scope
Integration of Hat Yai TMD Radar Station (`hyi` 240km) into FonMaYang backend, catalog, admin interface, and coverage map.

---

## 🛠️ Verification Steps & Commands

### 1. Backend Unit Tests (TDD Verification)
Run the unit test suite dedicated to Hat Yai station and adjacent southern radar stations:

```bash
backend/.venv/bin/pytest backend/tests/test_hat_yai_radar.py backend/tests/test_surat_thani_radar.py
```

**Expected Result:**
- All 8 unit tests pass cleanly in ~1.5s.
- `test_hat_yai_station_registered`: Verified registration in `STATIONS` and `KNOWN_TMD_RADAR_PRESETS`.
- `test_hat_yai_pin_pixel_location`: Verified center coordinates (`6.9248`, `100.4385`) map to pixel `(362, 362)` in cropped space.
- `test_hat_yai_maritime_and_terrain_colors_not_detected_as_rain`: Sea background and terrain green colors resolve to 0 dBZ.
- `test_hat_yai_legitimate_rain_detected`: Rain green/yellow colors detected as >= 20 dBZ.

### 2. Version & Documentation Synchronization
Verify version consistency across components:

```bash
cat VERSION
cat backend/VERSION
grep '"version"' frontend/package.json
head -n 20 CHANGELOG.md
```

**Expected Result:**
- Version string is synchronized to `0.72.29`.
- `CHANGELOG.md` lists `[0.72.29]` release notes.

---

## 📸 Screenshots / Artifacts
- Unit test verification log: All 8 tests passed in `test_hat_yai_radar.py` & `test_surat_thani_radar.py`.
