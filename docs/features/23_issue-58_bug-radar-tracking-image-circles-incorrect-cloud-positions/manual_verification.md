# Manual Verification Guide — Issue 58: Radar Tracking Circle Positions

## Prerequisites

```bash
cd /Users/oatrice/Software-projects/FonMaYang/backend
source venv/bin/activate  # or: . venv/bin/activate
```

---

## Step 1: Run Unit Test (Automated)

```bash
PYTHONPATH=. venv/bin/python tests/test_clustering.py
```

**Expected Result:** `TEST PASSED` — confirms BFS clustering correctly groups a contiguous cloud into 1 cluster with an accurate centroid.

---

## Step 2: Visual Sanity Check — Synthetic Radar Image

```bash
PYTHONPATH=. venv/bin/python tests/fetch_real_radar.py
open tests/synthetic_tracking_result.png
```

**Expected Result:**
- Two cloud blobs visible (green/orange circles drawn on frame)
- Each cloud has a tracking circle centered **on** the cloud mass, not offset to an edge
- Yellow arrow points in the storm's direction of travel
- Red crosshair user pin is visible

---

## Step 3: Before/After False Positive Comparison (Real TMD Radar)

```bash
PYTHONPATH=. venv/bin/python - << 'EOF'
import asyncio, httpx, io, cv2, math
import numpy as np
from PIL import Image, ImageSequence
from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.tmd_radar_config import DBZ_COLOR_MAPPING

async def main():
    url = "https://weather.tmd.go.th/kkn/kkn120_latest.gif"
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        r = await client.get(url)
    img_pil = Image.open(io.BytesIO(r.content))
    frames = [np.array(f.copy().convert("RGB")) for f in ImageSequence.Iterator(img_pil)]
    frame = frames[0]
    processor = TMDRadarProcessor("kkn120")
    px, py = processor.latlng_to_pixel(16.4322, 102.8236, is_loop=False)

    vis = cv2.cvtColor(frame.copy(), cv2.COLOR_RGB2BGR)
    crop_x0, crop_y0 = processor.config.static_crop_x, processor.config.static_crop_y
    crop_w, crop_h = processor.config.static_crop_width, processor.config.static_crop_height
    cv2.rectangle(vis, (crop_x0, crop_y0), (crop_x0+crop_w, crop_y0+crop_h), (0,200,0), 2)
    for y in range(crop_y0, crop_y0 + crop_h, 3):
        for x in range(crop_x0, crop_x0 + crop_w, 3):
            d = processor.get_dbz_at_pixel(frame, x, y)
            if d >= 20.0:
                cv2.circle(vis, (x, y), 2, (0, 255, 255), -1)
    cv2.drawMarker(vis, (px, py), (0, 0, 255), cv2.MARKER_CROSS, 30, 3)
    cv2.imwrite("tests/debug_rain_final.png", vis)
    print("Saved tests/debug_rain_final.png")

asyncio.run(main())
EOF
open tests/debug_rain_final.png
```

**Expected Result:**
- Cyan dots appear **only on actual rain cells** (usually northeast of KKN on current radar)
- No cyan dots on the legend strip (left side) or on rivers/terrain
- Green rectangle shows the valid radar crop zone

---

## Step 4: Test the Full Telegram Webhook (End-to-End)

1. Make sure the bot is running locally:
   ```bash
   PYTHONPATH=. venv/bin/python -m uvicorn app.main:app --reload --port 8080
   ```

2. **Important Pre-requisite:** The bot requires a known location to process radar. 
   - **Option A (Real test):** Send your Live Location or Pinned Location via Telegram attachment first.
   - **Option B (Dev mode):** Send `/devmock rain` to use a simulated state without needing a real location.

3. Send the command to the Telegram bot:
   - Send `/rain tmd-radar` (or the shorthand `/check` which we just added in the webhook router).

3. The bot should respond with:
   - A radar GIF (animated) with the user pin visible
   - A **tracking image** showing circles centered on cloud masses
   - A rain summary line (Thai text)

**Expected Result:**
- **If it is raining:** Tracking circles sit **on top of the green/yellow/red cloud blobs** in the radar image. ETAs and wind arrows point in physically plausible directions. No phantom circles appear on empty sky or rivers.
- **If the weather is clear:** The bot will say "ยังไม่มีแนวโน้มฝนตก" and the tracking image will show the map and your pin, but **no circles** will be drawn.
- **⚠️ Note on Rate Limits:** If you send commands too rapidly, Telegram may block the GIF with a `429 Too Many Requests` error. If this happens, wait 10-20 seconds before trying again.


---

## Step 5: Regression Check — Verify No Other Tests Broken

```bash
PYTHONPATH=. venv/bin/python -m pytest tests/ -v --timeout=30
```

**Expected Result:** All existing tests pass. `test_clustering.py::test_find_approaching_clouds_clustering` shows `PASSED`.
