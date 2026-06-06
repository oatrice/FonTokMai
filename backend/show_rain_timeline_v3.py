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

CONFIDENCE_CUTOFF_MIN = 90

def fmt_eta(minutes):
    m = int(round(minutes))
    if m < 60:
        return f"~{m}m"
    h = m // 60
    r = m % 60
    return f"~{h}h{r}m" if r else f"~{h}hr"

def find_all_approaching_clouds(img, prev_img, flow, user_x, user_y,
                                search_radius=80, min_dbz=20.0, cluster_dist=20):
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
                prev_x = int(round(sx - cvx))
                prev_y = int(round(sy - cvy))
                d_prev = processor.get_dbz_at_pixel(prev_img, prev_x, prev_y) if prev_img is not None else d
                candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))
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
        dbz_now  = max(g[4] for g in group)
        dbz_prev = max(g[5] for g in group)
        dist_c = math.sqrt((cx - user_x)**2 + (cy - user_y)**2)
        dot_c  = sum(g[7] for g in group) / len(group)
        eta_min = (dist_c / max(0.1, dot_c)) * 15
        if dbz_prev > 0:
            growth_rate = (dbz_now - dbz_prev) / dbz_prev
        else:
            growth_rate = 0.0
        eta_steps = eta_min / 15.0
        predicted_dbz = max(0.0, min(75.0, dbz_now * ((1 + growth_rate) ** eta_steps)))
        clusters.append({
            "cx": int(cx), "cy": int(cy),
            "dbz_now": dbz_now, "dbz_prev": dbz_prev,
            "growth_rate": growth_rate,
            "predicted_dbz": predicted_dbz,
            "dist": dist_c, "eta_min": eta_min,
        })
    clusters.sort(key=lambda c: c["eta_min"])
    return clusters

clouds = find_all_approaching_clouds(frames[-1], frames[-2], flow, px, py)

def dbz_to_color_bgr(dbz):
    if dbz >= 55: return (0, 0, 220)
    if dbz >= 40: return (0, 60, 255)
    if dbz >= 25: return (0, 165, 255)
    return (0, 220, 180)

def dbz_to_label_en(dbz):
    if dbz >= 55: return "Heavy+"
    if dbz >= 40: return "Heavy"
    if dbz >= 25: return "Moderate"
    return "Light"

def dbz_to_label_th(dbz):
    if dbz >= 55: return "ฝนหนักมาก ⛈"
    if dbz >= 40: return "ฝนหนัก 🌧"
    if dbz >= 25: return "ฝนปานกลาง 🌦"
    return "ฝนเบา 🌦"

# ===== Timeline Image =====
W, H = 900, 360
canvas = np.zeros((H, W, 3), dtype=np.uint8)
canvas[:] = (18, 20, 30)

T_MAX = max(200, max(c["eta_min"] for c in clouds) + 20) if clouds else 200
margin_l, margin_r = 80, 40
margin_t, margin_b = 100, 80
axis_w = W - margin_l - margin_r
axis_h = H - margin_t - margin_b

def t_to_x(t):
    return int(margin_l + (t / T_MAX) * axis_w)

for t in range(0, int(T_MAX)+1, 15):
    tx = t_to_x(t)
    cv2.line(canvas, (tx, margin_t), (tx, H-margin_b), (32,38,52), 1)

# Shade uncertain zone
cutoff_x = t_to_x(CONFIDENCE_CUTOFF_MIN)
overlay = canvas.copy()
cv2.rectangle(overlay, (cutoff_x, margin_t), (W-margin_r, H-margin_b), (50, 30, 20), -1)
cv2.addWeighted(overlay, 0.4, canvas, 0.6, 0, canvas)

# Dashed confidence line
for y in range(margin_t, H-margin_b, 10):
    cv2.line(canvas, (cutoff_x, y), (cutoff_x, min(y+6, H-margin_b)), (80,140,255), 2)
cv2.putText(canvas, "< Reliable", (cutoff_x-78, margin_t-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100,200,100), 1)
cv2.putText(canvas, "Uncertain >", (cutoff_x+6, margin_t-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80,140,255), 1)

# Axes
cv2.line(canvas, (margin_l, H-margin_b), (W-margin_r, H-margin_b), (200,200,200), 2)
cv2.line(canvas, (margin_l, margin_t), (margin_l, H-margin_b), (200,200,200), 2)

# X ticks
tick_step = 30
for t in range(0, int(T_MAX)+1, tick_step):
    tx = t_to_x(t)
    cv2.line(canvas, (tx, H-margin_b), (tx, H-margin_b+6), (180,180,180), 1)
    t_lbl = fmt_eta(t).replace("~", "")
    cv2.putText(canvas, t_lbl, (tx-16, H-margin_b+22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160,160,160), 1)

cv2.putText(canvas, "Time ahead ->", (W//2-50, H-16),
            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120,120,120), 1)

# Y reference lines
for dbz_ref, label in [(25, "25"), (40, "40"), (55, "55")]:
    bar_h_ref = int((dbz_ref / 75.0) * axis_h)
    ref_y = H - margin_b - bar_h_ref
    cv2.line(canvas, (margin_l-5, ref_y), (W-margin_r, ref_y), (45,45,58), 1)
    cv2.putText(canvas, label, (margin_l-38, ref_y+4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120,120,120), 1)
cv2.putText(canvas, "dBZ", (8, margin_t+10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140,140,140), 1)

# Title (English only in image)
cv2.putText(canvas, "Rain Timeline Forecast", (margin_l, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255,255,255), 2)
cv2.putText(canvas, f"16.121N 101.875E  |  Reliable: 0 - {CONFIDENCE_CUTOFF_MIN}min",
            (margin_l, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180,180,180), 1)

# Now marker
now_x = t_to_x(0)
cv2.line(canvas, (now_x, margin_t-18), (now_x, H-margin_b), (0,220,255), 2)
cv2.putText(canvas, "Now", (now_x+4, margin_t-20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0,220,255), 1)

# Bars
bar_w = 18
strongest_idx = max(range(len(clouds)), key=lambda i: clouds[i]["predicted_dbz"]) if clouds else -1

for i, c in enumerate(clouds[:10]):
    eta_min = c["eta_min"]
    predicted_dbz = c["predicted_dbz"]
    growth_rate = c["growth_rate"]
    will_dissipate = predicted_dbz < 15
    is_uncertain = eta_min > CONFIDENCE_CUTOFF_MIN

    tx = t_to_x(eta_min)
    col = dbz_to_color_bgr(predicted_dbz)

    if will_dissipate:
        col_fade = tuple(int(x * 0.25) for x in col)
        cv2.rectangle(canvas, (tx-bar_w//2, H-margin_b-20), (tx+bar_w//2, H-margin_b), col_fade, -1)
        cv2.line(canvas, (tx-10, H-margin_b-20), (tx+10, H-margin_b), (70,70,70), 2)
        cv2.line(canvas, (tx+10, H-margin_b-20), (tx-10, H-margin_b), (70,70,70), 2)
        cv2.putText(canvas, "diss.", (tx-18, H-margin_b-24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.34, (100,100,100), 1)
        continue

    bar_h = int((predicted_dbz / 75.0) * axis_h)
    bar_top = H - margin_b - bar_h

    # Highlight strongest
    if i == strongest_idx:
        cv2.rectangle(canvas, (tx-bar_w//2-4, bar_top-4), (tx+bar_w//2+4, H-margin_b+2), (0,0,140), -1)

    # Fade uncertain bars slightly
    draw_col = tuple(int(x * 0.55) for x in col) if is_uncertain else col
    cv2.rectangle(canvas, (tx-bar_w//2, bar_top), (tx+bar_w//2, H-margin_b), draw_col, -1)
    cv2.rectangle(canvas, (tx-bar_w//2, bar_top), (tx+bar_w//2, H-margin_b),
                  (180,180,180) if is_uncertain else (255,255,255), 1)

    # Growth arrow
    if growth_rate > 0.05:
        cv2.putText(canvas, "^", (tx-5, bar_top+16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,100), 1)
    elif growth_rate < -0.05:
        cv2.putText(canvas, "v", (tx-5, bar_top+16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80,80,255), 1)

    # ETA label (hr/min format)
    eta_lbl = fmt_eta(eta_min)
    label_col = (150,150,150) if is_uncertain else (230,230,230)
    cv2.putText(canvas, eta_lbl, (tx-22, bar_top-14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, label_col, 1)

    # DBZ value
    cv2.putText(canvas, f"{int(predicted_dbz)}", (tx-11, bar_top+32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)

    # Label under bar
    cv2.putText(canvas, dbz_to_label_en(predicted_dbz), (tx-26, H-margin_b+38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.30, draw_col, 1)

out_img = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/rain_timeline.png"
cv2.imwrite(out_img, canvas)
print(f"Saved: {out_img}")

# ===== Telegram Text (Thai OK here) =====
print()
print("=== Telegram Text ===")
shown = [c for c in clouds if c["predicted_dbz"] >= 15 and c["eta_min"] <= CONFIDENCE_CUTOFF_MIN]
uncertain = [c for c in clouds if c["predicted_dbz"] >= 15 and c["eta_min"] > CONFIDENCE_CUTOFF_MIN]

print(f"🌧 พยากรณ์ฝน — 16.121°N 101.875°E")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━")
for c in shown[:5]:
    gr = c["growth_rate"]
    trend = "📈" if gr > 0.05 else ("📉" if gr < -0.05 else "➡️")
    bar = "█" * int(c["predicted_dbz"] / 10)
    print(f"{fmt_eta(c['eta_min'])}  {bar:<6} {int(c['predicted_dbz'])} dBZ  {trend}")
if uncertain:
    print(f"┄ ⚠️ หลัง {CONFIDENCE_CUTOFF_MIN} นาที ความแม่นยำลดลง ┄")
    for c in uncertain[:2]:
        print(f"{fmt_eta(c['eta_min'])}  {int(c['predicted_dbz'])} dBZ  (ไม่แน่นอน)")
print(f"━━━━━━━━━━━━━━━━━━━━━━━━")
if shown:
    first = shown[0]
    strongest = max(shown, key=lambda c: c["predicted_dbz"])
    print(f"⏱ ฝนก้อนแรกใน {fmt_eta(first['eta_min'])}")
    print(f"⚡ ก้อนหนักสุด {int(strongest['predicted_dbz'])} dBZ ใน {fmt_eta(strongest['eta_min'])}")
else:
    print("ℹ️ ไม่พบฝนที่น่าเชื่อถือใน 90 นาทีข้างหน้า")
