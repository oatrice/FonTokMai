import cv2
import numpy as np
import pickle
import sys

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

with open("tmp/saved_frames_kkn240.pkl", "rb") as f:
    frames = pickle.load(f)

processor = TMDRadarProcessor(station_code="kkn240")

lat = 16 + 7/60 + 13.8/3600
lng = 101 + 52/60 + 31.7/3600
px, py = processor.latlng_to_pixel(lat, lng, processor.config)

flow = processor.calculate_optical_flow(frames)
vx, vy = processor.get_flow_vector_at(flow, px, py)

crop_size = 180
s_x = max(0, px - crop_size)
e_x = min(frames[0].shape[1], px + crop_size)
s_y = max(0, py - crop_size)
e_y = min(frames[0].shape[0], py + crop_size)

target_src_x = int(round(px - vx * 1))
target_src_y = int(round(py - vy * 1))

panels = []
for i in range(len(frames)):
    idx = -(i + 1)
    img = frames[idx].copy()

    # LINEAR estimate (no snap)
    lin_x = int(round(target_src_x - i * vx))
    lin_y = int(round(target_src_y - i * vy))

    # SNAP to max DBZ in R30 (old buggy behavior)
    max_d = 0
    snap_tx, snap_ty = lin_x, lin_y
    for dy in range(-30, 31):
        for dx in range(-30, 31):
            sx2 = lin_x + dx
            sy2 = lin_y + dy
            if 0 <= sx2 < img.shape[1] and 0 <= sy2 < img.shape[0]:
                d = processor.get_dbz_at_pixel(frames[idx], sx2, sy2)
                if d > max_d:
                    max_d = d
                    snap_tx = sx2
                    snap_ty = sy2

    c_img = img[s_y:e_y, s_x:e_x].copy()

    def lc(gx, gy):
        return (int(gx - s_x), int(gy - s_y))

    # User position
    ux, uy = lc(px, py)
    cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    cv2.putText(c_img, "YOU", (ux+6, uy-8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,255), 2)

    # LINEAR track = WHITE circle (correct)
    lx_l, ly_l = lc(lin_x, lin_y)
    cv2.circle(c_img, (lx_l, ly_l), 16, (255, 255, 255), 2)
    cv2.circle(c_img, (lx_l, ly_l), 3, (255, 255, 255), -1)

    # SNAP to max = RED circle (buggy)
    sx_l, sy_l = lc(snap_tx, snap_ty)
    cv2.circle(c_img, (sx_l, sy_l), 16, (0, 0, 255), 2)  # red = wrong

    label = "current" if i == 0 else f"{i*15}m ago"
    cv2.putText(c_img, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,255,255), 2)
    cv2.putText(c_img, f"White=linear  Red=snap(bug)", (8, c_img.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)

    panels.append(c_img)

panels.reverse()
top = np.hstack(panels[:3])
bot = np.hstack(panels[3:])
combined = np.vstack([top, bot])

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/tracked_cloud_new_coord.png"
cv2.imwrite(out, combined)
print(f"Saved: {out}")
