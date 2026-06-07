# Calculate Rain Cloud Trajectory (Issue #66)

## Goal
Improve the accuracy of rain cloud trajectory predictions. Currently, the system uses a simple dot product which only ensures the cloud is moving generally towards the user, but it could still pass alongside without intersecting. We will implement a Perpendicular Distance (Cross Track Error) check to ensure the cloud's actual trajectory will hit the user.

## User Review Required
- Is a `hit_radius` of 15 pixels (~15-20 km) acceptable for the tolerance of the perpendicular distance? This accounts for cloud expansion and optical flow slight inaccuracies.

## Proposed Changes

### `backend/app/services/tmd_radar_processor.py`
#### [MODIFY] `TMDRadarProcessor.find_approaching_clouds()`
- **Current Logic:** Uses `dot = (cvx * to_x + cvy * to_y) / dist > 0.1`.
- **New Logic:**
  - Add a parameter `hit_radius: int = 15`.
  - Ensure the cloud is moving towards the user (`dot > 0`).
  - Calculate the velocity magnitude: `v_mag = math.sqrt(cvx**2 + cvy**2)`.
  - Calculate the perpendicular distance: `perp_dist = abs(to_x * cvy - to_y * cvx) / v_mag`.
  - If `perp_dist > hit_radius`, exclude the pixel because it will miss the user.
- **Why:** This ensures we only track pixels that are on a direct collision course with the user's location, reducing false alarms from storms that are nearby but moving parallel to the user.

## Verification Plan
### Automated Tests
- No new automated tests are specified, but we will rely on `/devmock rain` and `/devmock storm` to visually verify the trajectory vectors and ETA.

### Manual Verification
- Use `/devmock rain` to verify that clouds heading towards the user are detected.
- Modify the mock cloud's movement vector `(vx, vy)` to pass *beside* the user, and verify that the system correctly ignores it.
