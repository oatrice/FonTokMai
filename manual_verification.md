# Manual Verification Plan: Radar Crop Fix

## Verification Steps
1. Navigate to the Admin Radar UI (`/admin/radar`).
2. Select the **Chainat (chn)** station (or any other station) from the list.
3. Click the new **"✨ Auto-Detect"** button. This will ignore the previous slider values, auto-detect the radar circle, and add a 10px padding to prevent the top from being cut off.
4. Observe the preview image. The blue crop box should now completely enclose the green radar circle with a small margin (padding) all around it. The top edge of the circle should no longer touch the blue bounding box.
5. Click **"💾 Submit to Neon DB"** to save the newly calculated, padded crop coordinates.
6. Trigger a webhook or wait for the worker to process the next image.
7. Verify the cropped image in Firebase Storage. It should no longer be missing the bottom, left, and right parts ("ตัดแหว่ง"), and the top should have the correct margin.

## Edge Cases
- If the radar circle is very close to the edge of the image (e.g., `< 10px` from the edge), the padding will be automatically clamped by `max(0, cx - r - padding)` to prevent out-of-bounds indexing.
- The `Preview (Use Sliders)` button still exists and allows you to test manual slider adjustments without resetting the auto-detect state.
