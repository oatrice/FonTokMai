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

# Flow is computed ONCE and shared across all users
flow = processor.calculate_optical_flow(frames)
print("Flow computed once. Now running per-user detection...")

def find_all_approaching_clouds(img, flow, user_x, user_y, search_radius=80, min_dbz=20.0, cluster_dist=20):
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

    clusters = []
    used = [False] * len(candidates)
    for i, c in enumerate(candidates):
        if used[i]:
            continue
        group = [c]
        used[i] = True
        for j, c2 in enumerate(candidates):
            if used[j]:
                continue
            if math.sqrt((c[0]-c2[0])**2 + (c[1]-c2[1])**2) < cluster_dist:
                group.append(c2)
                used[j] = True
        
        total_w = sum(g[4] for g in group)
        cx = sum(g[0]*g[4] for g in group) / total_w
        cy = sum(g[1]*g[4] for g in group) / total_w
        avg_vx = sum(g[2] for g in group) / len(group)
        avg_vy = sum(g[3] for g in group) / len(group)
        max_dbz = max(g[4] for g in group)
        dist_c = math.sqrt((cx - user_x)**2 + (cy - user_y)**2)
        dot_c = sum(g[6] for g in group) / len(group)
        eta_min = (dist_c / max(0.1, dot_c)) * 15
        clusters.append((int(cx), int(cy), avg_vx, avg_vy, max_dbz, dist_c, eta_min))
    
    clusters.sort(key=lambda c: c[5])
    return clusters

# Two users
users = {
    "User A\n17.839N 102.573E": processor.latlng_to_pixel(17.839305, 102.573027, processor.config),
    "User B\n16.121N 101.875E": processor.latlng_to_pixel(16 + 7/60 + 13.8/3600, 101 + 52/60 + 31.7/3600, processor.config),
}

user_colors = [(0, 0, 255), (255, 100, 0)]  # Red, Blue
cloud_colors = [(0, 255, 0), (0, 200, 255), (200, 100, 255), (0, 165, 255)]

# Build per-user storyboard side by side
crop_size = 150

all_user_rows = []
for user_idx, (user_name, (upx, upy)) in enumerate(users.items()):
    u_color = user_colors[user_idx]
    s_x = max(0, upx - crop_size)
    e_x = min(frames[0].shape[1], upx + crop_size)
    s_y = max(0, upy - crop_size)
    e_y = min(frames[0].shape[0], upy + crop_size)

    panels = []
    for i in range(len(frames)):
        idx = -(i + 1)
        img = frames[idx]
        clouds = find_all_approaching_clouds(img, flow, upx, upy)
        c_img = img[s_y:e_y, s_x:e_x].copy()

        def lc(gx, gy, sx=s_x, sy=s_y):
            return (int(gx - sx), int(gy - sy))

        ux, uy = lc(upx, upy)
        cv2.drawMarker(c_img, (ux, uy), u_color, cv2.MARKER_CROSS, 18, 2)

        for rank, cloud in enumerate(clouds[:4]):
            cx, cy, cvx, cvy, cdbz, dist, eta_min = cloud
            col = cloud_colors[rank % len(cloud_colors)]
            tx_l, ty_l = lc(cx, cy)
            r = max(12, int(cdbz / 4))
            cv2.circle(c_img, (tx_l, ty_l), r, col, 2)
            arr_end = lc(cx + int(cvx*4), cy + int(cvy*4))
            cv2.arrowedLine(c_img, (tx_l, ty_l), arr_end, col, 2, tipLength=0.3)
            cv2.putText(c_img, f"#{rank+1} {eta_min:.0f}m", 
                       (tx_l+r+2, ty_l+5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)

        frame_label = "now" if i == 0 else f"{i*15}m ago"
        cv2.putText(c_img, frame_label, (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)
        panels.append(c_img)
    
    panels.reverse()
    row = np.hstack(panels)
    
    # Label bar
    short_name = user_name.split('\n')[0]
    label_bar = np.zeros((28, row.shape[1], 3), dtype=np.uint8)
    cv2.rectangle(label_bar, (0,0), (label_bar.shape[1], 28), (30,30,30), -1)
    cv2.putText(label_bar, f"{short_name}  pixel=({upx},{upy})", (10, 19), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, u_color, 1)
    all_user_rows.append(np.vstack([label_bar, row]))

final = np.vstack(all_user_rows)

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/multi_user_cloud_tracking.png"
cv2.imwrite(out, final)
print(f"Saved: {out}")
