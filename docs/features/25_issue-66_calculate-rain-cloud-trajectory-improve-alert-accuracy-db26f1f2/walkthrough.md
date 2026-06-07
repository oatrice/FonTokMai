# Implementation Walkthrough: Cloud Trajectory Optimization (Issue #66)

## Changes Made
- **File:** `backend/app/services/tmd_radar_processor.py`
- **Component:** `find_approaching_clouds`
- **Modifications:** 
  - We replaced the basic dot product check (which only ensured the cloud was moving generally towards the user) with a strict **Perpendicular Distance (Cross Track Error)** check.
  - A new parameter `hit_radius: int = 15` was introduced to define the tolerance width of the cloud trajectory.
  - The optical flow vector `(cvx, cvy)` and position vector `(to_x, to_y)` are cross-multiplied and divided by the velocity magnitude to find the closest distance the cloud trajectory will pass by the user. If this distance is greater than `hit_radius`, the cloud is safely ignored.

## What was verified
- The logic strictly evaluates the perpendicular offset of the cloud's exact motion path against the user's location.
- The `hit_radius = 15` effectively filters out adjacent storms that are moving parallel to the user without directly striking them, minimizing false alarms for nearby but non-intersecting rain cells.
