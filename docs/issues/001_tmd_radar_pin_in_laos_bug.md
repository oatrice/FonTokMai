# Issue: "Pin in Laos" (TMD Radar Pin Misalignment for SKN240)

## Problem Description
The user reported that when querying the weather using the `/rain tmd home` command for coordinates in Kusuman, Sakon Nakhon (17.4142, 104.3943), the blue cross pin was misplaced on the returned radar image. The pin appeared across the Mekong River in Ban Nadon, Laos (shifted approximately 31km East and 27km North from the actual location).

## Root Cause Analysis: Failed Attempts & Misdiagnoses

### 1. First Attempt: Linear Interpolation vs Azimuthal Projection
- **Hypothesis:** We initially assumed the issue was caused by using simple Linear Interpolation to map lat/lng coordinates to pixels over a large 240km bounding box, ignoring the Earth's curvature.
- **Action:** We implemented an **Azimuthal Equidistant Projection** utilizing Haversine distance calculations in the `latlng_to_pixel` function.
- **Result (Failed):** The mathematical calculation became perfectly accurate. It calculated the target pixel as `(404, 297)` for Loop GIFs and `(475, 349)` for Static Images. However, when testing the bot live, the pin was *still* placed in Laos. The projection math was not the root cause.

### 2. Second Attempt: Firebase Cache Image Source Mismatch
- **Hypothesis:** We noticed that the Telegram bot fetches its images from a Firebase Storage cache (`url_t`) rather than polling the TMD website directly. We discovered that `weather_manager.py` hardcoded the fallback image type as `frame_source = "static_cache"`. However, the background cron jobs cache *both* Static images (800x800) and Loop GIFs (680x680) to the same field. When the bot pulled a 680x680 Loop GIF, the hardcoded assumption forced it to pass `is_loop=False` to the processor.
- **Action:** We implemented a dynamic height check to override the hardcoded assumption: `is_loop = curr_frame.shape[0] <= processor.config.loop_crop_height + processor.config.loop_crop_y + 10`.
- **Result (Failed):** The bot *still* placed the pin in Laos.

### 3. Third Attempt: Flawed Height Threshold Calculation
- **Hypothesis:** Why did the dynamic check fail? We broke down the formula for `skn240`:
  - `loop_crop_height` = 620
  - `loop_crop_y` = 24
  - Buffer = 10
  - Total Threshold = 654
  - **Actual Loop GIF Height** = 680
  Since `680 <= 654` evaluates to `False`, the system STILL treated the 680x680 Loop GIF as a Static Image. 
  *(Note: The original condition logic was implicitly tailored for `kkn240`, which has a 600px height, so it passed for Khon Kaen but failed silently for Sakon Nakhon).*
- **Result:** Because `is_loop=False` was passed, the processor applied the Static Image crop offsets `(475, 349)` onto the smaller `680x680` Loop image. This misapplied offset (shift of +71x, +52y) is precisely what threw the pin across the Mekong into Laos.

## Final Correct Solution
We discarded the tightly coupled bounding box threshold check and relied on a simpler, absolute truth: **TMD Static Images are always exactly 800x800 pixels**. Any image pulled from the cache with a dimension smaller than 800 is guaranteed to be a Loop GIF (e.g., 680x680 or 800x600).

**Code Fix applied to `weather_manager.py` and `tmd_radar_processor.py`:**
```python
# Safely detect if cached image is from loop GIF (height/width < 800) or static image
is_loop = frame.shape[0] < 800 or frame.shape[1] < 800
frame_source = "loop_gif" if is_loop else "static_cache"
```

This ensures that whenever the bot pulls the `skn240` 680x680 Loop GIF from the cache, `is_loop` evaluates to `True`, triggering the correct crop offsets and placing the pin accurately at `(404, 297)` in Kusuman.
