# Manual Verification Plan - Rayong (ryg) Radar Setup

- **Branch**: `[Current Branch]`
- **MR / Issue ID**: `#265` (or related issue)
- **Date**: 2026-08-11

---

## 📌 Prerequisites & Environment Setup
1. Ensure the web application (`http://localhost:3000`) and backend API are running locally.
2. Ensure the Telegram bot is running locally or deployed.
   ```bash
   # Run frontend (if not running)
   npm run dev
   # Run backend (if not running)
   poetry run uvicorn backend.app.main:app --reload
   ```

---

## 🧪 Verification Scenarios

### Scenario 1: Admin UI Preset & Auto-Detect Verification
- **Goal**: Verify that the `ryg` preset populates correctly and auto-detect calibration functions.
- **Steps**:
  1. Open the Web Admin at `http://localhost:3000/admin/radar`.
  2. Select **Rayong (240km) / ระยอง** (`ryg`) from the Presets Dropdown.
  3. Verify the form fields are prefilled correctly (`code: ryg`, `name: Rayong (240km) / ระยอง`, etc.).
  4. Click the **✨ Auto-Detect** button.
  5. Switch to the **`🌀 Loop GIF Frame (loop.gif)`** tab.
  6. Visually inspect the crop boundary overlay. Adjust the Interactive Crop Box if it does not perfectly align with the radar circle.
- **Expected Outcome**:
  - The preset fields load without error.
  - Auto-Detect successfully calculates a circle boundary (or a reasonable approximation that can be tuned manually).
  - The UI clearly overlays the calculated boundary on the loop GIF frame.

---

### Scenario 2: Save to Database & Cache Eviction
- **Goal**: Verify that saving the calibration persists to Neon DB and clears relevant caches.
- **Steps**:
  1. After confirming or adjusting the crop box in Scenario 1, click **💾 Submit to Neon DB**.
- **Expected Outcome**:
  - A success toast appears.
  - HTTP Status: `200 OK` for the save endpoint.
  - The database saves the `crop_x`, `crop_y`, `crop_width`, `crop_height` values correctly.
  - The system automatically triggers cache eviction (In-Memory + Firestore).

---

### Scenario 3: Telegram Bot End-to-End Test
- **Goal**: Verify the Telegram bot uses the newly calibrated `ryg` preset to render rain maps correctly.
- **Steps**:
  1. Open Telegram and send the command `/rain_pro ryg` (or `/rain_pro default` if `ryg` is configured as the default) to the bot.
- **Expected Outcome**:
  - The bot acknowledges the request immediately.
  - The background worker downloads the `ryg` radar frames, applies the saved crop offsets, and successfully renders the rain map.
  - The bot replies with the accurate, un-distorted rain map image.

---

## 📸 Proof of Verification (Artifacts & Logs)
- **Command Output / Test Logs Snippet**:
  ```text
  [Insert relevant log output for DB save or Telegram bot processing here]
  ```
- **Automated Verification Summary**:
  - Manual verification completed successfully by [User].
