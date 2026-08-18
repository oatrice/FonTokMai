# Manual Verification — Code Review Fixes & Testing Epic

**Branch:** `epic/radar-trajectory-webhooks-interactive-maps`  
**Commit:** `ed84413` + testing additions  
**Date:** 2026-08-17  

---

## Prerequisites

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
# → http://localhost:3000
```

---

## Scenario 1 — C1/C2: DB-down returns partial (not 500)

**Steps:**
```bash
# Stop DB / set wrong NEON_DSN
NEON_DSN="postgresql://invalid:invalid@invalid/invalid" uvicorn app.main:app --reload

curl http://localhost:8000/api/v1/radar/stations
```
**Expected:**
```json
{
  "stations": [],
  "error": "Partial data — DB unavailable",
  "partial": true
}
```
**Not expected:** HTTP 500, `NameError: STATIONS`, `UnboundLocalError: cache`

---

## Scenario 2 — M2: Stale station correctly shows "offline"

**Steps:**
```bash
# Manually insert a cache entry with empty frames & old timestamp
# (or wait 60+ min for a station that hasn't been polled)
curl http://localhost:8000/api/v1/radar/stations | python3 -m json.tool | grep -A3 '"code": "kkn240"'
```
**Expected (if last frame > 60 min ago):**
```json
{
  "code": "kkn240",
  "status": "offline",
  "latency_minutes": 90.0
}
```

---

## Scenario 3 — M3: kkn120 shows "delayed" not "offline"

**Steps:**
1. Open `http://localhost:3000/admin/radar`
2. Find station marker for "Khon Kaen 120km"
3. Check the status badge colour

**Expected:** Amber/yellow badge (delayed ~45 min), NOT red (offline)  
**Not expected:** Red "offline" badge for kkn120 when its parent kkn240 is active

---

## Scenario 4 — C3: SVG marker IDs are namespaced

**Steps:**
1. Open `http://localhost:3000/admin/radar`
2. Open browser DevTools → Elements
3. Search for `<marker` element in SVG

**Expected:** `<marker id="arrow-:r1:">` or similar React-generated unique ID  
**Not expected:** `<marker id="arrow">` (bare, causes collision on pages with multiple SVGs)

---

## Scenario 5 — H4: Zoom is multiplicative (×1.35 per step)

**Steps:**
1. Open `http://localhost:3000/admin/radar`
2. Click "+" zoom button once
3. Read zoom badge value

**Expected:** Badge shows `1.4x` (1.35 rounded to 1 decimal)  
4. Click "+" again → badge shows `1.8x` (1.35² ≈ 1.82)  
5. Click "-" → back to `1.4x`

**Not expected:** Additive steps (1.5x, 2.0x, 2.5x)

---

## Scenario 6 — M1: Lightning text suppressed when 'detected' key absent

**Telegram Test:**
```bash
# Send /rain_pro command, check advanced text response
# When backend returns: {"lightning": {"distance_km": 5.0}}  (no 'detected' key)
```
**Expected:** Lightning section NOT in Telegram message  
**Expected:** No `⚡` emoji, no `โดนฟ้าผ่า` text  
**Not expected:** Lightning warning triggered incorrectly

---

## Scenario 7 — Clusters endpoint has source & is_mock fields

**Steps:**
```bash
curl http://localhost:8000/api/v1/radar/clusters | python3 -m json.tool | head -5
```
**Expected:**
```json
{
  "clusters": [...],
  "source": "baseline_mock",
  "is_mock": true
}
```
When live cache is warm:
```json
{
  "source": "live_cache",
  "is_mock": false
}
```

---

## Scenario 8 — Issue #188: Cluster hover shows trajectory

**Steps:**
1. Open `http://localhost:3000/admin/radar`
2. Hover mouse over any storm cell cluster (coloured polygon)
3. Observe right side of screen

**Expected:**
- Trajectory preview card appears with cluster name, speed (km/h), heading direction
- Historical path arrows drawn on SVG map in faded blue

4. Move mouse away → card disappears  
5. Click cluster → card stays pinned with "📌 ปักหมุด" badge

---

## Automated Test Results

```bash
# Backend (run before MR merge)
cd backend && python3 -m pytest tests/ -q
# Expected: 500+ passed, ≤4 skipped, 0 failed

# Security suite
pytest tests/test_radar_security.py tests/test_radar_router_fixes.py tests/test_performance_polygon.py -v
# Expected: 39 passed

# Frontend unit tests
cd frontend && npm test -- --watchAll=false --ci
# Expected: 39 passed (1 pre-existing spiderfy test in progress)

# E2E (requires running dev server)
npm run test:e2e
```

---

## Closing Issues

This MR resolves the following code review findings:
- `C1` — STATIONS NameError in `/radar/stations` except block
- `C2` — UnboundLocalError: `cache` before assignment  
- `C3` — SVG marker ID collision (bare `"arrow"` → `useId()` namespaced)
- `H1` — Inline polygon computation → `useMemo`
- `H2` — Fetch proxy timeout (AbortController)
- `H4` — Additive zoom → multiplicative (×1.35)
- `M1` — `has_lightning` default True → False (needs `detected: True`)
- `M2` — Stale-station offline logic (empty frames + >60 min)
- `M3` — kkn120 fallback route.ts
- `M4` — Duplicate `style` prop on province paths
- `M5` — `getDbzColor`/`getStatusColor` extracted to `radarUtils.ts`
- `M6` — RadarCoverageMap zoom unified to ×1.35
- `L1` — Missing `is_active` default in `radar.py`
- `L2` — Import path fix in `test_line_integration.py`
