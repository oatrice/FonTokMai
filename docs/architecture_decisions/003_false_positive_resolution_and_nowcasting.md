# ADR 003: False Positive Resolution and Nowcasting Strategy

## Status
Accepted

## Context
The current rain alert system utilizes Rainbow.ai's global nowcast endpoint (`precip-global`), which relies on coarse global forecasting models with a wide bounding box. This approach caused a severe false positive issue (Issue #27) where users in clear zones (e.g., Tha Bo, Nong Khai) received alerts triggered by heavy thunderstorm cells across the border (e.g., Vientiane, Laos). The algorithm fired as soon as the precipitation rate exceeded 0.0, capturing noise and distant cells that were not tracking towards the user's location.

To resolve this and improve prediction accuracy, we need a new strategy for detecting and alerting on incoming rain.

## Decisions

We have decided to implement a four-pillar approach to overhaul the alert logic:

1. **Threshold Tuning (Issue #29)**
   - Increase the minimum precipitation rate threshold to trigger an alert (e.g., `RAIN_TRIGGER_THRESHOLD_MM=0.5`). This filters out model noise and light mist that do not warrant a notification.

2. **Geofence Tightening (Issue #30)**
   - Shrink the effective weather lookup radius to a strict 5–10 km perimeter around the user's coordinate to isolate local weather and prevent cross-border bleed.

3. **Transition to Real-time Local Radar (Issue #28)**
   - Replace the coarse global forecast model with the RainViewer Radar API.
   - RainViewer provides actual radar reflectivity (dBZ) data from local weather station networks, giving a precise picture of current precipitation intensity at a specific coordinate.

4. **Wind Vector Nowcasting (Issue #31)**
   - Incorporate wind speed and direction data (e.g., via Open-Meteo) to calculate the movement trajectory of storm cells.
   - Alerts will only fire if the storm cell's trajectory intersects the user's coordinate within the alert time window.

## Consequences

### Positive
- **Increased Accuracy:** Precision increases drastically by relying on actual radar data rather than wide global models.
- **Reduced False Positives:** Geofencing, thresholding, and wind trajectory checks ensure alerts only fire for relevant, approaching storms.
- **User Trust:** Fewer false alarms lead to higher confidence in the bot.

### Negative / Complexity
- **Implementation Complexity:** Decoding RainViewer radar tiles (PNG pixel data to dBZ) and computing trajectory vectors introduces significant mathematical and image-processing complexity compared to parsing a simple JSON response.
- **Dependency Management:** Relies on multiple data sources (RainViewer for radar, Open-Meteo for wind) which must be orchestrated efficiently.
- **Performance:** Processing radar tiles and computing vectors per user location during background tasks requires careful optimization to avoid timeouts.
