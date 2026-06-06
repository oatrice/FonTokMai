import asyncio
import cv2
import numpy as np
import sys
import math

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    
    px, py = 344, 144  # user coord

    # 3 user-observed cloud positions
    obs = {
        "45m ago": (330, 150),
        "30m ago": (360, 140),
        "current": (380, 110),
    }
    
    # Velocities between observations
    v_45_30 = (obs["30m ago"][0] - obs["45m ago"][0],
               obs["30m ago"][1] - obs["45m ago"][1])  # per 15 min
    v_30_now = (obs["current"][0] - obs["30m ago"][0],
                obs["current"][1] - obs["30m ago"][1])
    
    print("=== User Observed Trajectory ===")
    for t, pos in obs.items():
        print(f"  {t}: {pos}")
    print()
    print(f"Velocity 45m->30m: dx={v_45_30[0]}, dy={v_45_30[1]} px/15min")
    print(f"Velocity 30m->now: dx={v_30_now[0]}, dy={v_30_now[1]} px/15min")
    
    # Find closest approach to user
    # Interpolate: positions at t = 0(45m ago), 1(30m), 2(now)
    pts = [obs["45m ago"], obs["30m ago"], obs["current"]]
    min_dist = float('inf')
    min_t = None
    min_pos = None
    for i in range(len(pts)-1):
        for s in range(100):
            alpha = s / 100.0
            ix = pts[i][0] + alpha * (pts[i+1][0] - pts[i][0])
            iy = pts[i][1] + alpha * (pts[i+1][1] - pts[i][1])
            d = math.sqrt((ix - px)**2 + (iy - py)**2)
            if d < min_dist:
                min_dist = d
                min_t = i + alpha
                min_pos = (ix, iy)
    
    min_t_min = (min_t - 2) * 15  # negative = ago
    print(f"\nClosest approach to user:")
    print(f"  At T={min_t_min:.0f} min (negative = ago, 0 = now)")
    print(f"  Position: ({min_pos[0]:.0f}, {min_pos[1]:.0f})")
    print(f"  Distance: {min_dist:.1f} pixels ({min_dist * 0.692:.1f} km)")
    
    # Calculate system optical flow for comparison
    flow = processor.calculate_optical_flow(frames)
    sys_vx, sys_vy = processor.get_flow_vector_at(flow, px, py)
    print(f"\nSystem optical flow at user: vx={sys_vx:.1f}, vy={sys_vy:.1f}")
    avg_vx = (v_45_30[0] + v_30_now[0]) / 2
    avg_vy = (v_45_30[1] + v_30_now[1]) / 2
    print(f"User-observed avg velocity: vx={avg_vx:.1f}, vy={avg_vy:.1f}")
    
    # Draw composite: trajectory on current frame
    img = frames[-1].copy()
    crop_size = 250
    s_x = max(0, px - crop_size)
    e_x = min(img.shape[1], px + crop_size)
    s_y = max(0, py - crop_size)
    e_y = min(img.shape[0], py + crop_size)
    
    c_img = img[s_y:e_y, s_x:e_x].copy()
    
    def to_local(gx, gy):
        return (int(gx - s_x), int(gy - s_y))
    
    # Draw trajectory line
    colors = [(64, 64, 255), (0, 200, 255), (0, 255, 100)]  # 45m, 30m, now
    labels = ["45m ago", "30m ago", "Current"]
    traj_pts_local = []
    for (gx, gy), col, lab in zip(pts, colors, labels):
        lx, ly = to_local(gx, gy)
        traj_pts_local.append((lx, ly))
        cv2.circle(c_img, (lx, ly), 12, col, 2)
        cv2.putText(c_img, lab, (lx + 14, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
    
    # Draw trajectory arrows
    for i in range(len(traj_pts_local)-1):
        cv2.arrowedLine(c_img, traj_pts_local[i], traj_pts_local[i+1], (255,200,0), 2, tipLength=0.2)
    
    # User position
    ux, uy = to_local(px, py)
    cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
    cv2.putText(c_img, "YOU", (ux+5, uy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
    
    # Closest approach point
    cx_l, cy_l = to_local(min_pos[0], min_pos[1])
    cv2.circle(c_img, (cx_l, cy_l), 8, (255,255,255), -1)
    cv2.putText(c_img, f"Closest: {min_dist*0.7:.0f}km, {min_t_min:.0f}min", 
                (cx_l+5, cy_l+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
    cv2.line(c_img, (ux, uy), (cx_l, cy_l), (255,255,255), 1, cv2.LINE_AA)
    
    cv2.putText(c_img, "User-Observed Trajectory", (10, 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    
    out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/cloud_trajectory.png"
    cv2.imwrite(out, c_img)
    print(f"\nSaved: {out}")

asyncio.run(main())
