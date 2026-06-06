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
    # Sort by ETA (soonest first)
    clusters.sort(key=lambda c: c[6])
    return clusters

clouds = find_all_approaching_clouds(frames[-1], flow, px, py)

print(f"Total approaching clouds: {len(clouds)}")
for i, c in enumerate(clouds):
    print(f"  #{i+1}: ETA={c[6]:.0f}min DBZ={c[4]}")

def dbz_to_label(dbz):
    if dbz >= 55: return "ฝนหนักมาก ⛈", (0, 0, 220)
    if dbz >= 40: return "ฝนหนัก 🌧",    (0, 80, 255)
    if dbz >= 25: return "ฝนปานกลาง 🌦", (0, 180, 255)
    return "ฝนเบา 🌦",                    (0, 220, 180)

def dbz_to_color_bgr(dbz):
    """Color scale for bars"""
    if dbz >= 55: return (0, 0, 220)    # dark red
    if dbz >= 40: return (0, 60, 255)   # red-orange
    if dbz >= 25: return (0, 165, 255)  # orange
    return (0, 220, 180)                 # green

# ===== Draw Timeline Image =====
W, H = 860, 320
canvas = np.zeros((H, W, 3), dtype=np.uint8)
canvas[:] = (18, 20, 30)

T_MAX = max(180, max(c[6] for c in clouds) + 30) if clouds else 180
margin_l, margin_r = 80, 40
margin_t, margin_b = 90, 70
axis_w = W - margin_l - margin_r
axis_h = H - margin_t - margin_b

def t_to_x(t_min):
    return int(margin_l + (t_min / T_MAX) * axis_w)

# Background grid
for t in range(0, int(T_MAX)+1, 15):
    tx = t_to_x(t)
    cv2.line(canvas, (tx, margin_t), (tx, H-margin_b), (35,40,55), 1)

# Axis
cv2.line(canvas, (margin_l, H-margin_b), (W-margin_r, H-margin_b), (200,200,200), 2)
cv2.line(canvas, (margin_l, margin_t), (margin_l, H-margin_b), (200,200,200), 2)

# Ticks
tick_step = 30 if T_MAX > 200 else 15
for t in range(0, int(T_MAX)+1, tick_step):
    tx = t_to_x(t)
    cv2.line(canvas, (tx, H-margin_b), (tx, H-margin_b+6), (180,180,180), 1)
    cv2.putText(canvas, f"{int(t)}m", (tx-14, H-margin_b+22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160,160,160), 1)

cv2.putText(canvas, "นาทีจากนี้ →", (W//2-40, H-12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120,120,120), 1)

# Y-axis label
cv2.putText(canvas, "dBZ", (8, margin_t+10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150,150,150), 1)

# Y reference lines
for dbz_ref in [25, 40, 55]:
    bar_h_ref = int((dbz_ref / 75.0) * axis_h)
    ref_y = H - margin_b - bar_h_ref
    cv2.line(canvas, (margin_l-5, ref_y), (W-margin_r, ref_y), (50,50,65), 1)
    cv2.putText(canvas, str(dbz_ref), (margin_l-35, ref_y+4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120,120,120), 1)

# Title
cv2.putText(canvas, "Rain Timeline Forecast", (margin_l, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255,255,255), 2)
cv2.putText(canvas, f"16.121N 101.875E  |  {len(clouds)} clouds approaching",
            (margin_l, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180,180,180), 1)

# NOW marker
now_x = t_to_x(0)
cv2.line(canvas, (now_x, margin_t-15), (now_x, H-margin_b), (0,220,255), 2)
cv2.putText(canvas, "Now", (now_x+4, margin_t-18),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,220,255), 1)

# Find strongest cloud for highlight
strongest_idx = max(range(len(clouds)), key=lambda i: clouds[i][4]) if clouds else -1

bar_w = 18
for i, cloud in enumerate(clouds[:8]):
    cx, cy, cvx, cvy, dbz, dist, eta_min = cloud
    col = dbz_to_color_bgr(dbz)
    tx = t_to_x(eta_min)
    bar_h = int((dbz / 75.0) * axis_h)
    bar_top = H - margin_b - bar_h

    # Glow for strongest cloud
    if i == strongest_idx:
        cv2.rectangle(canvas, (tx - bar_w//2 - 4, bar_top - 4),
                      (tx + bar_w//2 + 4, H-margin_b+2), (0, 0, 180), -1)

    cv2.rectangle(canvas, (tx - bar_w//2, bar_top), (tx + bar_w//2, H-margin_b), col, -1)
    cv2.rectangle(canvas, (tx - bar_w//2, bar_top), (tx + bar_w//2, H-margin_b), (255,255,255), 1)

    # Diamond
    pts = np.array([[tx, bar_top-10],[tx+9,bar_top],[tx,bar_top+10],[tx-9,bar_top]], np.int32)
    cv2.fillPoly(canvas, [pts], col)

    # ETA label on top
    eta_lbl = f"~{int(eta_min)}m"
    lx = tx - 18
    if i == strongest_idx:
        cv2.putText(canvas, "⚡" + eta_lbl, (lx - 5, bar_top - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 200, 255), 1)
    else:
        cv2.putText(canvas, eta_lbl, (lx, bar_top - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220,220,220), 1)

    # DBZ inside bar
    cv2.putText(canvas, f"{int(dbz)}", (tx - 11, bar_top + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255,255,255), 1)

# Summary bar at bottom
if clouds:
    first = clouds[0]
    strongest = clouds[strongest_idx]
    sum_y = H - 14
    cv2.putText(canvas,
                f"ฝนก้อนแรก: ~{int(first[6])} นาที  |  ก้อนหนักสุด (55dBZ): ~{int(strongest[6])} นาที",
                (margin_l, sum_y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1)

out_img = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/rain_timeline.png"
cv2.imwrite(out_img, canvas)
print(f"\nSaved: {out_img}")

# ===== Telegram Text Version =====
print()
print("=== Telegram Text ===")
print(f"🌧 พยากรณ์ฝน — 16.121°N 101.875°E")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━")

SHOW_TOP = min(5, len(clouds))
# Always include strongest if not in top N
shown_indices = list(range(SHOW_TOP))
if strongest_idx not in shown_indices:
    shown_indices.append(strongest_idx)
    shown_indices.sort(key=lambda i: clouds[i][6])

for i in shown_indices:
    cx, cy, cvx, cvy, dbz, dist, eta_min = clouds[i]
    lbl, _ = dbz_to_label(dbz)
    bar_count = int(dbz / 10)
    bar = "█" * bar_count
    star = " ⚡" if i == strongest_idx else ""
    print(f"~{int(eta_min):>3} นาที  {bar:<6} {int(dbz)} dBZ  {lbl}{star}")

print(f"━━━━━━━━━━━━━━━━━━━━━━━━")
if clouds:
    first = clouds[0]
    strongest = clouds[strongest_idx]
    s_lbl, _ = dbz_to_label(strongest[4])
    print(f"⏱ ฝนก้อนแรกใน ~{int(first[6])} นาที")
    print(f"⚡ ก้อนหนักสุด {int(strongest[4])} dBZ ({s_lbl}) ใน ~{int(strongest[6])} นาที")
