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
flow = processor.calculate_optical_flow(frames)

lat = 16 + 7/60 + 13.8/3600
lng = 101 + 52/60 + 31.7/3600
px, py = processor.latlng_to_pixel(lat, lng, processor.config)

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
        if used[i]: continue
        group = [c]
        used[i] = True
        for j, c2 in enumerate(candidates):
            if used[j]: continue
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
    
    clusters.sort(key=lambda c: c[6])  # sort by ETA
    return clusters

clouds = find_all_approaching_clouds(frames[-1], flow, px, py)

def dbz_to_label(dbz):
    if dbz >= 55: return "ฝนหนักมาก", (0, 0, 220)
    if dbz >= 40: return "ฝนหนัก",    (0, 80, 255)
    if dbz >= 25: return "ฝนปานกลาง", (0, 180, 255)
    return "ฝนเบา",              (0, 220, 180)

# ===== Draw Timeline Image =====
W, H = 800, 300
canvas = np.zeros((H, W, 3), dtype=np.uint8)
canvas[:] = (20, 20, 30)

# Time axis: 0 to 120 min
T_MAX = 120
margin_l, margin_r = 80, 40
margin_t, margin_b = 80, 60
axis_w = W - margin_l - margin_r
axis_h = H - margin_t - margin_b

def t_to_x(t_min):
    return int(margin_l + (t_min / T_MAX) * axis_w)

# Draw axis line
cv2.line(canvas, (margin_l, H-margin_b), (W-margin_r, H-margin_b), (180,180,180), 1)

# Time ticks every 15 min
for t in range(0, T_MAX+1, 15):
    tx = t_to_x(t)
    cv2.line(canvas, (tx, H-margin_b), (tx, H-margin_b+6), (150,150,150), 1)
    cv2.line(canvas, (tx, margin_t), (tx, H-margin_b), (40,40,50), 1)
    cv2.putText(canvas, f"{t}m", (tx-12, H-margin_b+20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160,160,160), 1)

cv2.putText(canvas, "นาทีจากนี้ →", (W//2 - 40, H-10), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120,120,120), 1)

# NOW marker
now_x = t_to_x(0)
cv2.line(canvas, (now_x, margin_t-10), (now_x, H-margin_b), (0,200,255), 2)
cv2.putText(canvas, "ตอนนี้", (now_x-18, margin_t-15), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,200,255), 1)

# Title
cv2.putText(canvas, "Rain Timeline Forecast", (margin_l, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)
cv2.putText(canvas, f"16.121N 101.875E  ({len(clouds)} clouds approaching)", (margin_l, 52), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180,180,180), 1)

# Plot each cloud as a diamond + drop bar
cloud_colors_palette = [
    (0, 255, 60),
    (0, 200, 255),
    (200, 100, 255),
    (0, 165, 255),
    (255, 200, 0),
]

bar_y_base = H - margin_b
bar_h_max = axis_h

for i, cloud in enumerate(clouds[:6]):
    cx, cy, cvx, cvy, dbz, dist, eta_min = cloud
    label_str, col = dbz_to_label(dbz)
    col = cloud_colors_palette[i % len(cloud_colors_palette)]
    
    tx = t_to_x(eta_min)
    
    # Bar height = DBZ intensity
    bar_h = int((dbz / 75.0) * bar_h_max)
    bar_top = bar_y_base - bar_h
    
    # Filled bar (thin)
    bar_w = 12
    cv2.rectangle(canvas, (tx - bar_w//2, bar_top), (tx + bar_w//2, bar_y_base), 
                  col, -1)
    cv2.rectangle(canvas, (tx - bar_w//2, bar_top), (tx + bar_w//2, bar_y_base), 
                  (255,255,255), 1)
    
    # Diamond on top
    pts = np.array([[tx, bar_top-10], [tx+8, bar_top], [tx, bar_top+10], [tx-8, bar_top]], np.int32)
    cv2.fillPoly(canvas, [pts], col)
    
    # ETA label
    label_txt = f"#{i+1} {eta_min:.0f}m"
    cv2.putText(canvas, label_txt, (tx - 20, bar_top - 18), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1)
    
    # DBZ label inside bar
    cv2.putText(canvas, f"{dbz:.0f}", (tx - 10, bar_top + 22), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1)

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/rain_timeline.png"
cv2.imwrite(out, canvas)
print(f"Saved: {out}")

# Also print text version (Telegram style)
print()
print("=== Telegram Text Version ===")
print(f"🌧 Rain Timeline สำหรับ 16.121°N 101.875°E")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
for i, cloud in enumerate(clouds[:5]):
    cx, cy, cvx, cvy, dbz, dist, eta_min = cloud
    lbl, _ = dbz_to_label(dbz)
    bar_count = int(dbz / 10)
    bar = "█" * bar_count
    print(f"#{i+1} ~{eta_min:.0f} นาที  {bar} {dbz:.0f} dBZ ({lbl})")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
if clouds:
    first_eta = clouds[0][6]
    max_dbz = max(c[4] for c in clouds)
    max_lbl, _ = dbz_to_label(max_dbz)
    print(f"⚡ ฝนจะเริ่มใน ~{first_eta:.0f} นาที  ความแรงสูงสุด: {max_dbz:.0f} dBZ ({max_lbl})")
