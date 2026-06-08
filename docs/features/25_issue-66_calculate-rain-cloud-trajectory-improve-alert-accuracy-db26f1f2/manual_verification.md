# Manual Verification Guide

Follow these steps to manually test the new TMD Radar Cache system and the color mapping adjustments:

**Step 1: Run the automated cache test script**
- Open your terminal and ensure you are in the root directory of the project (`/Users/oatrice/Software-projects/FonMaYang`).
- Execute the test script with the following command:
  ```bash
  PYTHONPATH=backend .venv/bin/python test_cache_system.py
  ```

**Step 2: Verify the output logs**
- **Phase 1 (Write):** Verify that the script successfully fetches from TMD and uploads to Firebase Storage. You should see logs like `Cached static image for kkn240` and `Updated Firestore radar_latest_cache`.
- **Phase 2 (Database):** Verify that it successfully found cache metadata in Firestore. It should display the `Static URL`, `Loop URL`, and `Timestamp` that were just saved.
- **Phase 3 (Read):** Verify that the processor successfully downloaded the static image and extracted frames from the Loop GIF using the cache. You should see the log `Successfully loaded static_url ... from Firebase Storage Cache`.

**Expected Result:**
The script completes without errors, proving the end-to-end cache flow works (TMD -> Firebase Storage -> Firestore -> Predictor).

**Step 3: Verify the Color Mapping and Trajectory improvements (Issue #66)**
- Run the visual test script using the `new` logic mode:
  ```bash
  PYTHONPATH=backend .venv/bin/python test_custom_image.py <path_to_a_radar_gif> --mode new
  ```
- Check the generated image `mock_test_result_new.jpg` and `mock_test_debug_pixels.jpg`.
- **Expected Result:** You should see that false-positive background colors are ignored, green clouds are preserved, and clouds that miss the user (Cross Track Error > 15-20px) are ignored, while clouds heading directly towards the user show an accurate ETA.
