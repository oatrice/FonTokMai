import cv2
import numpy as np
import pickle
import sys

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

with open("tmp/saved_frames_kkn240.pkl", "rb") as f:
    frames = pickle.load(f)

processor = TMDRadarProcessor(station_code="kkn240")

# New coordinate
lat = 16 + 7/60 + 13.8/3600   # 16.12050
lng = 101 + 52/60 + 31.7/3600  # 101.87547
px, py = processor.latlng_to_pixel(lat, lng, processor.config)
print(f"New coord: ({lat:.5f}, {lng:.5f}) → pixel ({px}, {py})")

# Check DBZ at this location for each frame
print("\nDBZ values per frame:")
for i in range(len(frames)):
    idx = -(i + 1)
    d = processor.get_dbz_at_pixel(frames[idx], px, py)
    d_r30 = processor._get_max_dbz_in_radius(frames[idx], px, py, radius=30)
    label = "current" if i == 0 else f"{i*15}m ago"
    print(f"  {label}: DBZ@point={d}, MaxDBZ R30={d_r30}")

# Build grid overlay for this new location - all frames
panels = []
crop_size = 200
s_x = max(0, px - crop_size)
e_x = min(frames[0].shape[1], px + crop_size)
s_y = max(0, py - crop_size)
e_y = min(frames[0].shape[0], py + crop_size)

for i in range(len(frames)):
    idx = -(i + 1)
    img = frames[idx].copy()
    
    # Grid
    step = 25
    for x in range(0, img.shape[1], step):
        if s_x <= x < e_x:
            cx = x - s_x
            c_img_h = e_y - s_y
            img_copy_x = img[s_y:e_y, s_x:e_x]
            cv2.line(img_copy_x, (cx, 0), (cx, c_img_h), (80, 80, 80), 1)
            cv2.putText(img_copy_x, str(x), (cx+2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200,200,200), 1)
    
    c_img = img[s_y:e_y, s_x:e_x].copy()
    
    for y in range(0, img.shape[0], step):
        if s_y <= y < e_y:
            cy = y - s_y
            cv2.line(c_img, (0, cy), (e_x-s_x, cy), (80, 80, 80), 1)
            cv2.putText(c_img, str(y), (3, cy-2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200,200,200), 1)
    
    ux = px - s_x
    uy = py - s_y
    cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
    cv2.putText(c_img, "NEW", (ux+8, uy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
    
    label = "current" if i == 0 else f"{i*15}m ago"
    cv2.putText(c_img, label, (10, e_y-s_y-12), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,255), 2)
    panels.append(c_img)

panels.reverse()
top = np.hstack(panels[:3])
bot = np.hstack(panels[3:])
combined = np.vstack([top, bot])

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/grid_overlay.png"
cv2.imwrite(out, combined)
print(f"\nSaved: {out}")
