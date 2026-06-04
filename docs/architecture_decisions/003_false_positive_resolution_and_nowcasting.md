# ADR 003: False Positive Resolution and Nowcasting Strategy

## Status
Superseded by ADR 004 (for Points 3 and 4)

## Context
The current rain alert system utilizes Rainbow.ai's global nowcast endpoint (`precip-global`), which relies on coarse global forecasting models with a wide bounding box. This approach caused a severe false positive issue (Issue #27) where users in clear zones (e.g., Tha Bo, Nong Khai) received alerts triggered by heavy thunderstorm cells across the border (e.g., Vientiane, Laos). The algorithm fired as soon as the precipitation rate exceeded 0.0, capturing noise and distant cells that were not tracking towards the user's location.

To resolve this and improve prediction accuracy, we need a new strategy for detecting and alerting on incoming rain.

## Decisions

We have decided to implement a four-pillar approach to overhaul the alert logic:

1. **Threshold Tuning (Issue #29) - [Accepted & Active]**
   - Increase the minimum precipitation rate threshold to trigger an alert (e.g., `RAIN_TRIGGER_THRESHOLD_MM=0.5`). This filters out model noise and light mist that do not warrant a notification.

2. **Geofence Tightening (Issue #30) - [Accepted & Active]**
   - Shrink the effective weather lookup radius to a strict 5–10 km perimeter around the user's coordinate to isolate local weather and prevent cross-border bleed.

3. **Transition to Real-time Local Radar (Issue #28) - [Superseded]**
   - *Original Plan:* Replace the coarse global forecast model with the RainViewer Radar API.
   - *Current Status:* Superseded by ADR 004. RainViewer lacks vector data APIs for commercial use, making it unsuitable for robust backend calculations.

4. **Wind Vector Nowcasting (Issue #31) - [Superseded]**
   - *Original Plan:* Incorporate wind speed and direction data to calculate the movement trajectory of storm cells manually.
   - *Current Status:* Superseded by ADR 004. Replaced by Xweather's native AI storm tracking (`stormcells`), which calculates complex kinematics accurately.

## Consequences

### Positive
- **Increased Accuracy:** Precision increases drastically by relying on actual data rather than wide global models.
- **Reduced False Positives:** Geofencing and thresholding ensure alerts only fire for relevant, approaching storms.
- **User Trust:** Fewer false alarms lead to higher confidence in the bot.

### Negative / Complexity
- The complex pixel-decoding and wind vector math approaches originally proposed were deemed too complicated and unreliable to build from scratch, leading directly to the strategic pivot documented in ADR 004.
