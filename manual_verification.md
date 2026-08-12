# Manual Verification Guide: Fix Contour Point X/Y Coordinate Unpacking

## Overview
- **Issue/Bug:** Neon Contour in Telegram `/rain_pro` and tracking image generator was misaligned / transposed relative to the rain cloud clusters.
- **Root Cause:** In `backend/app/services/tmd_radar/tracking.py` (lines 483 and 818), pixel tuples `(px, py)` from `c_orig["pixels"]` were unpacked as `for py, px in c_orig["pixels"]`. This caused the X coordinate (element 0) to be assigned to `py` and Y coordinate (element 1) to `px`, effectively swapping X and Y when drawing contour polygons on screen.
- **Fix:** Corrected `for py, px in c_orig["pixels"]` to `for px, py in c_orig["pixels"]` in `tracking.py`.

---

## 🧪 Automated Tests
Run unit tests to verify coordinate alignment and test suite stability:
```bash
./backend/venv/bin/pytest backend/tests/test_neon_contour_coordinates.py backend/tests/test_tmd_processor.py -v
```

**Expected Outcome:**
- All 21 tests pass without errors.
- `test_neon_contour_pixel_coordinates_alignment` passes, confirming X and Y coordinates map directly to screen canvas coordinates without inversion.

---

## 📱 Manual Verification Steps (Telegram / Web)

### Prerequisites
1. Backend server running locally or deployed.
2. Access to Telegram Bot.

### Steps
1. Open Telegram and send command `/rain_pro default` (or `/rain_pro ryg`).
2. Inspect the returned tracking image.
3. Observe the Neon Contour overlays (Magenta / Green / Yellow polygons).

### Expected Result
- Every Neon Contour outline and transparent fill aligns precisely over the rain cloud clusters (no diagonal flip or offset).
- Bounding boxes, centroids, and contour glows fit the cloud boundaries exactly.
