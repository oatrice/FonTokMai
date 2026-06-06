import asyncio
import cv2
import numpy as np
import sys
import math

sys.path.append("/Users/oatrice/Software-projects/FonMaYang/backend")
from app.services.tmd_radar_processor import TMDRadarProcessor

def farneback_flow(prev_gray, curr_gray, winsize=15):
    return cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None,
        pyr_scale=0.5, levels=5, winsize=winsize,
        iterations=5, poly_n=7, poly_sigma=1.5, flags=0
    )

def template_matching_flow(prev_gray, curr_gray, seed_x, seed_y, patch_r=30, search_r=80):
    """Extract patch around seed point in prev frame, find best match in curr frame."""
    h, w = prev_gray.shape
    
    # Extract patch
    px1 = max(0, seed_x - patch_r)
    px2 = min(w, seed_x + patch_r)
    py1 = max(0, seed_y - patch_r)
    py2 = min(h, seed_y + patch_r)
    template = prev_gray[py1:py2, px1:px2].astype(np.float32)
    
    if template.size == 0:
        return 0.0, 0.0
    
    # Search region in curr frame
    sx1 = max(0, seed_x - search_r)
    sx2 = min(w, seed_x + search_r)
    sy1 = max(0, seed_y - search_r)
    sy2 = min(h, seed_y + search_r)
    search = curr_gray[sy1:sy2, sx1:sx2].astype(np.float32)
    
    if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
        return 0.0, 0.0
    
    result = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(result)
    
    # Convert max_loc to flow vector
    match_x = sx1 + max_loc[0] + patch_r
    match_y = sy1 + max_loc[1] + patch_r
    
    vx = match_x - seed_x
    vy = match_y - seed_y
    return float(vx), float(vy)

async def main():
    processor = TMDRadarProcessor(station_code="kkn240")
    frames = await processor.fetch_loop_gif_and_extract_frames()
    
    px, py = 344, 144
    cloud_x, cloud_y = 360, 140  # user-observed cloud at current (closest to 30m ago)
    
    # Ground truth from user visual observations
    gt_vx, gt_vy = 25.0, -20.0  # avg of (30,-10) and (20,-30)
    
    # Prepare grayscale frames
    grays = [processor.extract_rain_mask(f) for f in frames]
    
    prev_gray = grays[-2]
    curr_gray = grays[-1]
    
    results = {}
    
    # 1. Farneback winsize 15 (current)
    flow15 = farneback_flow(prev_gray, curr_gray, winsize=15)
    vx15, vy15 = flow15[py, px], flow15[py, px]
    vx15_c, vy15_c = flow15[cloud_y, cloud_x, 0], flow15[cloud_y, cloud_x, 1]
    results["Farneback w=15"] = (flow15[py, px, 0], flow15[py, px, 1], vx15_c, vy15_c)
    
    # 2. Farneback winsize 30
    flow30 = farneback_flow(prev_gray, curr_gray, winsize=30)
    results["Farneback w=30"] = (flow30[py, px, 0], flow30[py, px, 1], flow30[cloud_y, cloud_x, 0], flow30[cloud_y, cloud_x, 1])
    
    # 3. Farneback winsize 50
    flow50 = farneback_flow(prev_gray, curr_gray, winsize=50)
    results["Farneback w=50"] = (flow50[py, px, 0], flow50[py, px, 1], flow50[cloud_y, cloud_x, 0], flow50[cloud_y, cloud_x, 1])
    
    # 4. Template Matching
    tm_vx, tm_vy = template_matching_flow(prev_gray, curr_gray, cloud_x, cloud_y, patch_r=30, search_r=80)
    results["Template Match"] = (tm_vx, tm_vy, tm_vx, tm_vy)
    
    print(f"Ground truth (user visual): vx={gt_vx:.1f}, vy={gt_vy:.1f}")
    print(f"User coord (px,py) = ({px},{py}), Cloud coord = ({cloud_x},{cloud_y})")
    print()
    print(f"{'Method':<20} {'vx@user':>8} {'vy@user':>8} {'vx@cloud':>10} {'vy@cloud':>10} {'err@cloud':>10}")
    print("-"*70)
    for name, (vxu, vyu, vxc, vyc) in results.items():
        err = math.sqrt((vxc - gt_vx)**2 + (vyc - gt_vy)**2)
        print(f"{name:<20} {vxu:>8.1f} {vyu:>8.1f} {vxc:>10.1f} {vyc:>10.1f} {err:>10.1f}")
    
    # Build zoomed-in comparison image (4 panels)
    crop_size = 100  # tighter zoom
    imgs = []
    
    for name, (vxu, vyu, vxc, vyc) in results.items():
        img = frames[-1].copy()
        
        s_x = max(0, px - crop_size)
        e_x = min(img.shape[1], px + crop_size)
        s_y = max(0, py - crop_size)
        e_y = min(img.shape[0], py + crop_size)
        c_img = img[s_y:e_y, s_x:e_x].copy()
        
        def lc(gx, gy):
            return (int(gx - s_x), int(gy - s_y))
        
        # User marker
        ux, uy = lc(px, py)
        cv2.drawMarker(c_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, 15, 2)
        
        # Arrow from user coord following THIS method's flow
        arr_end = lc(px + int(vxu * 3), py + int(vyu * 3))
        cv2.arrowedLine(c_img, (ux, uy), arr_end, (0, 255, 0), 2, tipLength=0.3)
        
        # Arrow from cloud coord
        cx_l, cy_l = lc(cloud_x, cloud_y)
        cv2.circle(c_img, (cx_l, cy_l), 8, (0, 255, 255), 2)
        arr_c_end = lc(cloud_x + int(vxc * 3), cloud_y + int(vyc * 3))
        cv2.arrowedLine(c_img, (cx_l, cy_l), arr_c_end, (0, 255, 255), 2, tipLength=0.3)
        
        # Ground truth arrow from cloud
        gt_end = lc(cloud_x + int(gt_vx * 3), cloud_y + int(gt_vy * 3))
        cv2.arrowedLine(c_img, (cx_l, cy_l), gt_end, (0, 165, 255), 2, tipLength=0.3)
        
        cv2.putText(c_img, name, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        cv2.putText(c_img, f"v=({vxc:.0f},{vyc:.0f})", (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,255), 1)
        cv2.putText(c_img, f"GT=({gt_vx:.0f},{gt_vy:.0f})", (5, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,165,255), 1)
        
        imgs.append(c_img)
    
    combined = np.hstack(imgs)
    legend = np.zeros((40, combined.shape[1], 3), dtype=np.uint8)
    cv2.putText(legend, "Green=flow@user  Cyan=flow@cloud  Orange=GroundTruth", 
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,200), 1)
    out_img = np.vstack([combined, legend])
    
    out = "/Users/oatrice/Software-projects/FonMaYang/docs/features/21_issue-56-57_feature-display-tmd-radar-images-latest-loop-directly-a54897f0/flow_method_comparison.png"
    cv2.imwrite(out, out_img)
    print(f"\nSaved: {out}")

asyncio.run(main())
