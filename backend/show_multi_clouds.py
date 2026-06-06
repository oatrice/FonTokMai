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

def find_all_approaching_clouds(img, flow, user_x, user_y, search_radius=80, min_dbz=20.0, cluster_dist=20):
    """
    Find all distinct approaching cloud clusters within search_radius.
    Returns list of (cx, cy, vx, vy, dbz, dist, eta_min) sorted by distance.
    """
    candidates = []
    for dy in range(-search_radius, search_radius + 1, 2):
        for dx in range(-search_radius, search_radius + 1, 2):
            sx = user_x + dx
            sy = user_y + dy
            if not (0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]):
                continue
            d = processor.get_dbz_at_pixel(img, sx, sy)
            if d < min_dbz:
                continue
            cvx, cvy = processor.get_flow_vector_at(flow, sx, sy)
            to_x = user_x - sx
            to_y = user_y - sy
            dist = math.sqrt(to_x**2 + to_y**2)
            if dist == 0:
                continue
            dot = (cvx * to_x + cvy * to_y) / dist
            if dot > 0:
                candidates.append((sx, sy, cvx, cvy, d, dist, dot))

    if not candidates:
        return []

    # Simple clustering: greedy merge
    clusters = []
    used = [False] * len(candidates)
    for i, c in enumerate(candidates):
        if used[i]:
            continue
        # Gather all within cluster_dist
        group = [c]
        used[i] = True
        for j, c2 in enumerate(candidates):
            if used[j]:
                continue
            dx2 = c[0] - c2[0]
            dy2 = c[1] - c2[1]
            if math.sqrt(dx2**2 + dy2**2) < cluster_dist:
                group.append(c2)
                used[j] = True
        
        # Weighted centroid by dbz
        total_w = sum(g[4] for g in group)
        cx = sum(g[0]*g[4] for g in group) / total_w
        cy = sum(g[1]*g[4] for g in group) / total_w
        avg_vx = sum(g[2] for g in group) / len(group)
        avg_vy = sum(g[3] for g in group) / len(group)
        max_dbz = max(g[4] for g in group)
        dist_c = math.sqrt((cx - user_x)**2 + (cy - user_y)**2)
        dot_c = sum(g[6] for g in group) / len(group)
        eta_steps = dist_c / max(0.1, dot_c)
        eta_min = eta_steps * 15
        
        clusters.append((int(cx), int(cy), avg_vx, avg_vy, max_dbz, dist_c, eta_min))
    
    clusters.sort(key=lambda c: c[5])  # sort by distance (closest first)
    return clusters

# Color palette for top clouds
colors = [
    (0, 255, 0),    # Green = closest
    (0, 200, 255),  # Cyan
    (255, 200, 0),  # Blue
    (200, 100, 255),# Purple
    (0, 165, 255),  # Orange
]

crop_size = 180
s_x = max(0, px - crop_size)
e_x = min(frames[0].shape[1], px + crop_size)
s_y = max(0, py - crop_size)
e_y = min(frames[0].shape[0], py + crop_size)

panels = []
for i in range(len(frames)):
    idx = -(i + 1)
    img = frames[idx]
    
    clouds = find_all_approaching_clouds(img, flow, px, py, search_radius=80)
    
    c_img = img[s_y:e_y, s_x:e_x].copy()
    
    def lc(gx, gy):
        return (int(gx - s_x), int(gy - s_y))
    
    ux, uy = lc(px, py)
    cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    
    for rank, cloud in enumerate(clouds[:5]):
        cx, cy, cvx, cvy, cdbz, dist, eta_min = cloud
        col = colors[rank % len(colors)]
        tx_l, ty_l = lc(cx, cy)
        
        # Circle radius scales with DBZ
        r = max(12, int(cdbz / 4))
        cv2.circle(c_img, (tx_l, ty_l), r, col, 2)
        cv2.circle(c_img, (tx_l, ty_l), 3, col, -1)
        
        # Arrow: flow direction
        arr_end = lc(cx + int(cvx * 4), cy + int(cvy * 4))
        cv2.arrowedLine(c_img, (tx_l, ty_l), arr_end, col, 2, tipLength=0.3)
        
        # Label
        label_text = f"#{rank+1} {eta_min:.0f}min"
        cv2.putText(c_img, label_text, (tx_l + r + 3, ty_l + 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
    
    frame_label = "current" if i == 0 else f"{i*15}m ago"
    cv2.putText(c_img, frame_label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,255,255), 2)
    cv2.putText(c_img, f"{len(clouds)} clouds", (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200,200,200), 1)
    panels.append(c_img)

panels.reverse()
top = np.hstack(panels[:3])
bot = np.hstack(panels[3:])
combined = np.vstack([top, bot])

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/tracked_cloud_new_coord.png"
cv2.imwrite(out, combined)
print(f"Saved: {out}")
