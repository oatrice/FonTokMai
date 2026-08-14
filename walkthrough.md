# Walkthrough: TMD Radar Dynamic Station Management & Nationwide Auto-Calibration

This Merge Request integrates nationwide dynamic TMD radar stations into FonMaYang, replacing hardcoded setups with a flexible database repository, automated circle calibration, and an interactive admin portal.

---

## 1. Automated Calibration & Registry Architecture (Issue #99, #52)
- **Dynamic Radar Station Registry (`DynamicRadarRegistry`)**: Implemented database-driven radar configuration with Neon PostgreSQL persistence and a 60-second in-memory TTL cache to eliminate redundant DB round-trips.
- **Nationwide Coverage (99% Coverage Across 13 Stations)**:
  - **Bangkok / Central:** Suvarnabhumi (`svp240`), Chainat (`chn`).
  - **Northeast:** Khon Kaen (`kkn120`, `kkn240`), Sakon Nakhon (`skn240`), Ubon Ratchathani (`ubn240`).
  - **North:** Chiang Rai (`cri`), Phitsanulok (`phs`), Tak / Doi Muser (`tak`).
  - **East:** Rayong (`ryg`).
  - **South:** Chumphon (`cmp`), Surat Thani (`srt`), Hat Yai (`hyi`).
- **Auto-Calibration Pipeline**: OpenCV Hough Circle detection automatically discovers radar canvas center boundaries and derives crop bounds.

---

## 2. Web Admin UI & Radar Coverage Map
- **Interactive Fine-Tuning Dashboard (`/admin/radar`)**: Interactive Next.js dashboard featuring draggable/resizable crop handles, simulated Telegram radar preview, and direct station seeding/saving.
- **Province Coverage Highlighting (`RadarCoverageMap.tsx`)**: SVG map rendering with GeoJSON boundaries and dynamic `clipPath` highlighting.

---

## 3. Bot UX & Resilient Geometry Projection
- **Projection Accuracy**: Per-station support for `linear` (equirectangular) and `azimuthal` (equidistant) coordinate projections ensuring GPS user pins land with sub-pixel precision.
- **False-Positive Noise Filtering**: Exclusion of background terrain greens and maritime blue colors in `IGNORED_COLORS` to prevent false rain alarms in coastal/mountainous regions.
- **Fast Developer Aliases**: Supported `/rain_pro_d` and `/rain d` fast location aliases for rapid Telegram and LINE weather queries.

---

## 4. Verification & Testing Summary
- **Backend Unit Tests**: Over 460 unit and integration tests passing (`pytest`), including dedicated suites for each regional station.
- **Frontend Production Build**: `next build` compiled cleanly with zero TypeScript errors.
- **Deployment Sync**: Verified Cloud Run environment variable synchronization.
