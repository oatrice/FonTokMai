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

# Ground truth from user visual: comparing consecutive frame pairs
# frames[-4] to frames[-3] = 45m→30m ago: cloud moved (330,150)→(360,140)
# frames[-2] to frames[-1] = 15m ago→now: cloud moved from some estimate to (380,110)
gt_pairs = {
    "45m→30m": {
        "prev_idx": -4, "curr_idx": -3,
        "seed": (330, 150),  # cloud position in prev frame
        "gt_vx": 30.0, "gt_vy": -10.0
    },
    "30m→15m": {
        "prev_idx": -3, "curr_idx": -2,
        "seed": (360, 140),  # cloud position in prev frame
        "gt_vx": 15.0, "gt_vy": -20.0  # interpolated
    },
    "15m→now": {
        "prev_idx": -2, "curr_idx": -1,
        "seed": (370, 125),  # interpolated
        "gt_vx": 20.0, "gt_vy": -30.0
    },
}

def calc_farneback(prev_gray, curr_gray, winsize=15):
    return cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=5, winsize=winsize,
        iterations=5, poly_n=7, poly_sigma=1.5, flags=0
    )

def calc_template_match(prev_gray, curr_gray, seed_x, seed_y, patch_r=25, search_r=70):
    h, w = prev_gray.shape
    px1, px2 = max(0, seed_x-patch_r), min(w, seed_x+patch_r)
    py1, py2 = max(0, seed_y-patch_r), min(h, seed_y+patch_r)
    template = prev_gray[py1:py2, px1:px2].astype(np.float32)
    if template.size == 0:
        return 0.0, 0.0
    sx1, sx2 = max(0, seed_x-search_r), min(w, seed_x+search_r)
    sy1, sy2 = max(0, seed_y-search_r), min(h, seed_y+search_r)
    search = curr_gray[sy1:sy2, sx1:sx2].astype(np.float32)
    if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
        return 0.0, 0.0
    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    match_x = sx1 + max_loc[0] + patch_r
    match_y = sy1 + max_loc[1] + patch_r
    return float(match_x - seed_x), float(match_y - seed_y)

print(f"{'Pair':<12} {'Method':<18} {'vx':>7} {'vy':>7} {'GT_vx':>7} {'GT_vy':>7} {'Error':>7}")
print("-"*70)

panels_all = []

for pair_name, cfg in gt_pairs.items():
    prev_img = frames[cfg["prev_idx"]]
    curr_img = frames[cfg["curr_idx"]]
    prev_gray = processor.extract_rain_mask(prev_img)
    curr_gray = processor.extract_rain_mask(curr_img)
    sx, sy = cfg["seed"]
    gt_vx, gt_vy = cfg["gt_vx"], cfg["gt_vy"]
    
    methods = {
        "Farneback w=15": calc_farneback(prev_gray, curr_gray, 15),
        "Farneback w=30": calc_farneback(prev_gray, curr_gray, 30),
        "Farneback w=50": calc_farneback(prev_gray, curr_gray, 50),
    }
    
    tm_vx, tm_vy = calc_template_match(prev_gray, curr_gray, sx, sy)
    
    # Visualize this pair: prev | curr | arrows panel
    crop = 120
    px_center, py_center = 344, 144
    s_x = max(0, px_center - crop)
    e_x = min(prev_img.shape[1], px_center + crop)
    s_y = max(0, py_center - crop)
    e_y = min(prev_img.shape[0], py_center + crop)
    
    pair_panels = []
    
    for method_name, flow in list(methods.items()) + [("Template Match", None)]:
        if method_name == "Template Match":
            vx, vy = tm_vx, tm_vy
        else:
            vx, vy = flow[sy, sx, 0], flow[sy, sx, 1]
        
        err = math.sqrt((vx - gt_vx)**2 + (vy - gt_vy)**2)
        print(f"{pair_name:<12} {method_name:<18} {vx:>7.1f} {vy:>7.1f} {gt_vx:>7.1f} {gt_vy:>7.1f} {err:>7.1f}")
        
        # Draw on curr frame
        c_img = curr_img[s_y:e_y, s_x:e_x].copy()
        
        def lc(gx, gy):
            return (int(gx - s_x), int(gy - s_y))
        
        # User marker
        ux, uy = lc(344, 144)
        cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 14, 2)
        
        # Cloud seed in this frame
        cx_l, cy_l = lc(sx, sy)
        cv2.circle(c_img, (cx_l, cy_l), 6, (0, 255, 255), 2)
        
        scale = 3
        # Calc'd arrow
        arr_end = lc(sx + int(vx * scale), sy + int(vy * scale))
        cv2.arrowedLine(c_img, (cx_l, cy_l), arr_end, (0, 255, 0), 2, tipLength=0.3)
        
        # GT arrow
        gt_end = lc(sx + int(gt_vx * scale), sy + int(gt_vy * scale))
        cv2.arrowedLine(c_img, (cx_l, cy_l), gt_end, (0, 140, 255), 2, tipLength=0.3)
        
        cv2.putText(c_img, method_name, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255,255,255), 1)
        cv2.putText(c_img, f"v=({vx:.0f},{vy:.0f})", (4, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)
        cv2.putText(c_img, f"GT=({gt_vx:.0f},{gt_vy:.0f}) err={err:.0f}", (4, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,140,255), 1)
        
        pair_panels.append(c_img)
    
    print()
    
    row = np.hstack(pair_panels)
    # Add label bar
    label_bar = np.zeros((28, row.shape[1], 3), dtype=np.uint8)
    cv2.putText(label_bar, f"{pair_name}  (cloud seed {cfg['seed']})", 
                (10, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
    panels_all.append(np.vstack([label_bar, row]))

combined = np.vstack(panels_all)

legend = np.zeros((30, combined.shape[1], 3), dtype=np.uint8)
cv2.putText(legend, "Green arrow=calculated flow  Orange arrow=user ground truth  Cyan circle=cloud seed", 
            (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200,200,200), 1)
final = np.vstack([combined, legend])

out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/flow_method_comparison.png"
cv2.imwrite(out, final)
print(f"Saved: {out}")
