- Step 1: Navigate to the `backend` directory in your terminal.
- Step 2: Run the automated test suite by executing `python -m pytest tests/`.
- Expected Result: You should see that all tests related to `BaseWeatherService`, `RainViewerService`, and `RainbowService` pass successfully.

- Step 1: Test RainViewer Integration locally.
- Step 2: Create a scratch python file (e.g., `test_rainviewer.py`) that initializes `RainViewerService` and calls `await get_current_radar_metadata()`. Run it via `python test_rainviewer.py`.
- Expected Result: The terminal outputs a valid dictionary containing `timestamp` and a valid `map_layer` URL format.

- Step 1: Test Rainbow API Integration locally.
- Step 2: In the same scratch file, initialize `RainbowService` and call `await predict_rain_by_location(17.1664, 104.1486)` (Sakon Nakhon coordinates).
- Expected Result: The terminal outputs a dictionary containing a `predictions` list with time and rain data.
