# Manual Verification

## Feature: Hat Yai Radar Crop Calibration

### 1. Prerequisites
- The backend application is running.
- Ensure that the latest configuration changes in `backend/app/services/tmd_radar_catalog.py` and `backend/app/services/tmd_radar_config.py` are loaded.

### 2. Synchronization Step
Sync the updated radar configuration to the database by triggering the seed endpoint. 
If testing locally via the FastAPI server, you can do this by navigating to the Swagger UI (`/docs`) and executing the `POST /api/v1/admin/radar/seed` endpoint, or using curl if you know the exact port your server is running on:
```bash
# Example curl (replace 8000 with your actual backend port and add Auth token if required)
curl -X POST http://localhost:8000/api/v1/admin/radar/seed
```

### 3. Verification Steps
1. Open the Web Admin Telegram simulator debugger.
2. Trigger the Hat Yai radar check: `/rain_pro tmd radar` (or whichever command is mapped to testing `hyi`).
3. Check the output logs or the debugger interface.
4. Verify the following expected output:
   - **Deviation ($\Delta X, \Delta Y$)** should be significantly closer to `0px, 0px`.
   - **Center of Blue Crop Box** should match the **True Station/Radar Circle Center** at `X: 402, Y: 400 px`.

### 4. Edge Cases
- If the deviation is still large, verify that the Neon Postgres cache is cleared and that the database actually contains the updated `static_crop_x = 42` and `static_crop_y = 40` for the `hyi` code. The radar cache system uses a TTL of 60 seconds, so you may need to wait up to a minute before re-triggering.
