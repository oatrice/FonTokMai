import cv2
import numpy as np
import pickle
import sys
import math

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

with open("tmp/saved_frames_kkn240.pkl", "rb") as f:
    frames = pickle.load(f)

processor = TMDRadarProcessor(station_code="kkn240")

lat = 16 + 7/60 + 13.8/3600
lng = 101 + 52/60 + 31.7/3600
px, py = processor.latlng_to_pixel(lat, lng, processor.config)

flow = processor.calculate_optical_flow(frames)

def find_approaching_cloud_center(img, flow, user_x, user_y, search_radius=80, min_dbz=20.0):
    """
    Scan all rain pixels within search_radius of user.
    For each, check if the flow vector at that pixel points TOWARD user.
    Return the one closest to user that is also approaching.
    """
    best = None
    best_score = float('inf')

    for dy in range(-search_radius, search_radius + 1, 2):
        for dx in range(-search_radius, search_radius + 1, 2):
            sx = user_x + dx
            sy = user_y + dy
            if not (0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]):
                continue
            
            d = processor.get_dbz_at_pixel(img, sx, sy)
            if d < min_dbz:
                continue
            
            # Get flow at this rain pixel
            vx, vy = processor.get_flow_vector_at(flow, sx, sy)
            
            # Direction from this cloud pixel toward user
            to_user_x = user_x - sx
            to_user_y = user_y - sy
            dist = math.sqrt(to_user_x**2 + to_user_y**2)
            if dist == 0:
                continue
            
            # Dot product: positive = moving toward user
            dot = (vx * to_user_x + vy * to_user_y) / dist
            
            if dot > 0:  # approaching
                # Score = distance (prefer closer clouds that are approaching)
                score = dist
                if score < best_score:
                    best_score = score
                    best = (sx, sy, vx, vy, d, dot, dist)
    
    return best

# Visualize per frame
crop_size = 180
s_x = max(0, px - crop_size)
e_x = min(frames[0].shape[1], px + crop_size)
s_y = max(0, py - crop_size)
e_y = min(frames[0].shape[0], py + crop_size)

panels = []
for i in range(len(frames)):
    idx = -(i + 1)
    img = frames[idx]
    
    result = find_approaching_cloud_center(img, flow, px, py, search_radius=80)
    
    c_img = img[s_y:e_y, s_x:e_x].copy()
    
    def lc(gx, gy):
        return (int(gx - s_x), int(gy - s_y))
    
    ux, uy = lc(px, py)
    cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    
    if result:
        cx, cy, cvx, cvy, cdbz, dot, dist = result
        tx_l, ty_l = lc(cx, cy)
        
        # Green circle = approaching cloud
        cv2.circle(c_img, (tx_l, ty_l), 16, (0, 255, 0), 2)
        cv2.circle(c_img, (tx_l, ty_l), 3, (255,255,255), -1)
        
        # Arrow: where this cloud pixel is heading (scaled)
        arr_end = lc(cx + int(cvx * 4), cy + int(cvy * 4))
        cv2.arrowedLine(c_img, (tx_l, ty_l), arr_end, (0, 255, 120), 2, tipLength=0.3)
        
        # Dashed line to user
        cv2.line(c_img, (tx_l, ty_l), (ux, uy), (100, 100, 100), 1, cv2.LINE_AA)
        
        eta_steps = dist / max(0.1, dot)
        cv2.putText(c_img, f"DBZ={cdbz:.0f} dist={dist:.0f}px", (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,255,0), 1)
        cv2.putText(c_img, f"ETA~{eta_steps:.0f}steps={eta_steps*15:.0f}min", (8, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,255,120), 1)
    else:
        cv2.putText(c_img, "No approaching cloud", (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100,100,255), 1)
    
    label = "current" if i == 0 else f"{i*15}m ago"
    cv2.putText(c_img, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,255,255), 2)
    panels.append(c_img)

panels.reverse()
top = np.hstack(panels[:3])
bot = np.hstack(panels[3:])
combined = np.vstack([top, bot])

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/tracked_cloud_new_coord.png"
cv2.imwrite(out, combined)
print(f"Saved: {out}")
