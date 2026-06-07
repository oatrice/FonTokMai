import argparse
import cv2
import numpy as np
import sys
import os
import math
from PIL import Image, ImageSequence

# Add backend to sys.path so we can import the processor
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from app.services.tmd_radar_processor import TMDRadarProcessor

def extract_frames_from_gif(gif_path):
    frames = []
    try:
        with Image.open(gif_path) as img:
            for frame in ImageSequence.Iterator(img):
                frame_rgb = frame.convert('RGB')
                cv_img = np.array(frame_rgb)
                cv_img = cv_img[:, :, ::-1].copy() # RGB to BGR
                frames.append(cv_img)
    except Exception as e:
        print(f"Error reading GIF: {e}")
    return frames

def find_approaching_clouds_old_logic(processor, curr_frame, prev_frame, flow, user_x, user_y, search_radius=80, min_dbz=20.0, cluster_dist=20):
    """
    This is the EXACT old logic before Issue 66 was implemented.
    It uses simple `dot < 0.1` filtering without Cross Track Error.
    """
    is_loop = flow.shape[0] <= processor.config.loop_crop_height + processor.config.loop_crop_y + 10
    crop_x0 = processor.config.loop_crop_x if is_loop else processor.config.static_crop_x
    crop_y0 = processor.config.loop_crop_y if is_loop else processor.config.static_crop_y
    crop_w  = processor.config.loop_crop_width if is_loop else processor.config.static_crop_width
    crop_h  = processor.config.loop_crop_height if is_loop else processor.config.static_crop_height
    valid_x_min = crop_x0
    valid_x_max = crop_x0 + crop_w
    valid_y_min = crop_y0
    valid_y_max = crop_y0 + crop_h

    candidates = []
    
    debug_total = 0
    debug_valid_crop = 0
    debug_min_dbz = 0
    debug_dot_pass = 0
    max_dbz_found = 0
    max_dot_found = -999.0
    
    for dy in range(-search_radius, search_radius + 1, 2):
        for dx in range(-search_radius, search_radius + 1, 2):
            sx = user_x + dx
            sy = user_y + dy
            debug_total += 1
            if not (valid_x_min <= sx < valid_x_max and valid_y_min <= sy < valid_y_max):
                continue
            if not (0 <= sx < curr_frame.shape[1] and 0 <= sy < curr_frame.shape[0]):
                continue
            debug_valid_crop += 1
                
            d = processor.get_dbz_at_pixel(curr_frame, sx, sy)
            if d > max_dbz_found:
                max_dbz_found = d
            if d < min_dbz:
                continue
            debug_min_dbz += 1
                
            cvx, cvy = processor.get_flow_vector_at(flow, sx, sy)
            to_x = user_x - sx
            to_y = user_y - sy
            dist = math.sqrt(to_x ** 2 + to_y ** 2)
            if dist == 0:
                continue
            dot = (cvx * to_x + cvy * to_y) / dist
            if dot > max_dot_found:
                max_dot_found = dot
            
            # OLD LOGIC: Only checking dot product > 0.1
            if dot < 0.1:
                continue
            debug_dot_pass += 1
                
            prev_x = int(round(sx - cvx))
            prev_y = int(round(sy - cvy))
            d_prev = processor.get_dbz_at_pixel(prev_frame, prev_x, prev_y) if prev_frame is not None else d
            candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))

    print(f"DEBUG LOOP: Total={debug_total}, ValidCrop={debug_valid_crop}, MinDbzPassed={debug_min_dbz}, DotPassed={debug_dot_pass}")
    print(f"DEBUG STATS: Max DBZ Found={max_dbz_found}, Max Dot Found={max_dot_found}")

    if not candidates:
        return []

    clusters = []
    used = [False] * len(candidates)
    for i, c in enumerate(candidates):
        if used[i]:
            continue
        group = [c]
        used[i] = True
        queue = [c]
        while queue:
            curr = queue.pop(0)
            for j, c2 in enumerate(candidates):
                if not used[j] and math.sqrt((curr[0] - c2[0])**2 + (curr[1] - c2[1])**2) < cluster_dist:
                    group.append(c2)
                    used[j] = True
                    queue.append(c2)
                    
        if len(group) < 5:
            continue
            
        total_w = sum(g[4] for g in group)
        cx = int(sum(g[0] * g[4] for g in group) / total_w)
        cy = int(sum(g[1] * g[4] for g in group) / total_w)
        avg_vx = sum(g[2] for g in group) / len(group)
        avg_vy = sum(g[3] for g in group) / len(group)
        dbz_now = max(g[4] for g in group)
        dbz_prev = max(g[5] for g in group)
        growth_rate = dbz_now - dbz_prev
        predicted_dbz = dbz_now + growth_rate * 2
        dist_c = math.sqrt((cx - user_x) ** 2 + (cy - user_y) ** 2)
        dot_c = sum(g[7] for g in group) / len(group)
        
        if abs(dot_c) < 0.1: dot_c = 0.1 if dot_c >= 0 else -0.1
        eta_min = (dist_c / dot_c) * 15.0
        
        clusters.append({
            "cx": cx, "cy": cy,
            "vx": avg_vx, "vy": avg_vy,
            "dbz_now": dbz_now,
            "dbz_prev": dbz_prev,
            "growth_rate": growth_rate,
            "predicted_dbz": predicted_dbz,
            "dist": dist_c,
            "eta_min": eta_min,
        })
        
    return clusters

def find_approaching_clouds_new_debug(processor, curr_frame, prev_frame, flow, user_x, user_y, search_radius=80, min_dbz=20.0, cluster_dist=20, hit_radius=15, debug_img=None):
    """
    Debug version of the NEW logic to print exactly why clouds are filtered.
    Draws debug pixels on `debug_img` if provided.
    """
    is_loop = flow.shape[0] <= processor.config.loop_crop_height + processor.config.loop_crop_y + 10
    crop_x0 = processor.config.loop_crop_x if is_loop else processor.config.static_crop_x
    crop_y0 = processor.config.loop_crop_y if is_loop else processor.config.static_crop_y
    crop_w  = processor.config.loop_crop_width if is_loop else processor.config.static_crop_width
    crop_h  = processor.config.loop_crop_height if is_loop else processor.config.static_crop_height
    valid_x_min = crop_x0
    valid_x_max = crop_x0 + crop_w
    valid_y_min = crop_y0
    valid_y_max = crop_y0 + crop_h

    candidates = []
    
    print("\n--- NEW LOGIC DEBUG (Rejected Pixels) ---")
    rejected_dot = 0
    rejected_vmag = 0
    rejected_cte = 0
    
    for dy in range(-search_radius, search_radius + 1, 2):
        for dx in range(-search_radius, search_radius + 1, 2):
            sx = user_x + dx
            sy = user_y + dy
            if not (valid_x_min <= sx < valid_x_max and valid_y_min <= sy < valid_y_max): continue
            if not (0 <= sx < curr_frame.shape[1] and 0 <= sy < curr_frame.shape[0]): continue
            d = processor.get_dbz_at_pixel(curr_frame, sx, sy)
            if d < min_dbz: continue
            
            # Anti-noise check
            neighbors = 0
            for nx, ny in [(sx-1, sy), (sx+1, sy), (sx, sy-1), (sx, sy+1)]:
                if 0 <= nx < curr_frame.shape[1] and 0 <= ny < curr_frame.shape[0]:
                    if processor.get_dbz_at_pixel(curr_frame, nx, ny) >= min_dbz:
                        neighbors += 1
            if neighbors < 2:
                continue
                
            cvx, cvy = processor.get_flow_vector_at(flow, sx, sy)
            to_x = user_x - sx
            to_y = user_y - sy
            dist = math.sqrt(to_x ** 2 + to_y ** 2)
            if dist == 0: continue
            
            dot = (cvx * to_x + cvy * to_y) / dist
            if dot <= 0:
                rejected_dot += 1
                if debug_img is not None:
                    # Red dot for moving away
                    cv2.circle(debug_img, (int(sx), int(sy)), 1, (0, 0, 255), -1)
                continue
                
            v_mag = math.sqrt(cvx ** 2 + cvy ** 2)
            if v_mag < 0.1:
                rejected_vmag += 1
                if debug_img is not None:
                    # White dot for too slow
                    cv2.circle(debug_img, (int(sx), int(sy)), 1, (255, 255, 255), -1)
                continue
                
            perp_dist = abs(to_x * cvy - to_y * cvx) / v_mag
            if perp_dist > hit_radius:
                rejected_cte += 1
                if debug_img is not None:
                    # Yellow dot for Cross Track Error
                    cv2.circle(debug_img, (int(sx), int(sy)), 1, (0, 255, 255), -1)
                continue
                
            if debug_img is not None:
                # Green dot for passing all filters
                cv2.circle(debug_img, (int(sx), int(sy)), 1, (0, 255, 0), -1)
                
            prev_x = int(round(sx - cvx))
            prev_y = int(round(sy - cvy))
            d_prev = processor.get_dbz_at_pixel(prev_frame, prev_x, prev_y) if prev_frame is not None else d
            candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))

    print(f"Pixels rejected due to Dot <= 0 (moving away): {rejected_dot}")
    print(f"Pixels rejected due to V_mag < 0.1 (too slow): {rejected_vmag}")
    print(f"Pixels rejected due to Cross Track Error > {hit_radius} (will miss user): {rejected_cte}")
    print(f"Pixels passed all checks: {len(candidates)}\n")

    if not candidates:
        return []

    clusters = []
    used = [False] * len(candidates)
    for i, c in enumerate(candidates):
        if used[i]:
            continue
        group = [c]
        used[i] = True
        queue = [c]
        while queue:
            curr = queue.pop(0)
            for j, c2 in enumerate(candidates):
                if not used[j] and math.sqrt((curr[0] - c2[0])**2 + (curr[1] - c2[1])**2) < cluster_dist:
                    group.append(c2)
                    used[j] = True
                    queue.append(c2)
                    
        if len(group) < 5:
            continue
            
        total_w = sum(g[4] for g in group)
        cx = int(sum(g[0] * g[4] for g in group) / total_w)
        cy = int(sum(g[1] * g[4] for g in group) / total_w)
        avg_vx = sum(g[2] for g in group) / len(group)
        avg_vy = sum(g[3] for g in group) / len(group)
        dbz_now = max(g[4] for g in group)
        dbz_prev = max(g[5] for g in group)
        growth_rate = dbz_now - dbz_prev
        predicted_dbz = dbz_now + growth_rate * 2
        dist_c = math.sqrt((cx - user_x) ** 2 + (cy - user_y) ** 2)
        dot_c = sum(g[7] for g in group) / len(group)
        
        if abs(dot_c) < 0.1: dot_c = 0.1 if dot_c >= 0 else -0.1
        eta_min = (dist_c / dot_c) * 15.0
        
        clusters.append({
            "cx": cx, "cy": cy,
            "vx": avg_vx, "vy": avg_vy,
            "dbz_now": dbz_now,
            "dbz_prev": dbz_prev,
            "growth_rate": growth_rate,
            "predicted_dbz": predicted_dbz,
            "dist": dist_c,
            "eta_min": eta_min,
        })
        
    return clusters

def main():
    parser = argparse.ArgumentParser(description="Test radar logic with a static image or an animated GIF loop.")
    parser.add_argument("image", help="Path to your radar image (.jpg / .png / .gif)")
    parser.add_argument("--mode", choices=["old", "new"], default="new", help="Logic mode: 'old' (Dot Product only) or 'new' (Cross Track Error)")
    parser.add_argument("--lat", type=float, default=None, help="User latitude")
    parser.add_argument("--lng", type=float, default=None, help="User longitude")
    parser.add_argument("--user_x_1280", type=int, default=711, help="User X pixel in 1280x1280 scale")
    parser.add_argument("--user_y_1280", type=int, default=346, help="User Y pixel in 1280x1280 scale")
    parser.add_argument("--vx", type=float, default=-1.0, help="[Static only] Simulated wind X vector")
    parser.add_argument("--vy", type=float, default=0.5, help="[Static only] Simulated wind Y vector")
    parser.add_argument("--station", default="kkn240", help="Radar station code")
    parser.add_argument("--hit-radius", type=int, default=15, help="Perpendicular distance tolerance in pixels (New mode only)")
    
    args = parser.parse_args()
    
    processor = TMDRadarProcessor(args.station)
    
    if args.lat is not None and args.lng is not None:
        px, py = processor.latlng_to_pixel(args.lat, args.lng)
        if px is None:
            print(f"Error: Coordinate {args.lat}, {args.lng} is outside the {args.station} radar bounds.")
            return
    else:
        # Convert 1280x1280 scale to 800x800 scale (the internal scale)
        px = int(args.user_x_1280 * 800 / 1280)
        py = int(args.user_y_1280 * 800 / 1280)
    is_gif = args.image.lower().endswith(".gif")
    
    if is_gif:
        print(f"Loaded GIF loop: {args.image}")
        frames = extract_frames_from_gif(args.image)
        if len(frames) < 2:
            print("Error: GIF must have at least 2 frames for Optical Flow.")
            return
            
        print(f"Extracted {len(frames)} frames. Calculating REAL Optical Flow...")
        
        # Resize logic to fix scaled up images
        resized_frames = []
        for f in frames:
            if f.shape[1] != 800 or f.shape[0] != 800:
                f = cv2.resize(f, (800, 800), interpolation=cv2.INTER_NEAREST)
            resized_frames.append(f)
        frames = resized_frames
        
        prev_frame = frames[-2]
        curr_frame = frames[-1]
        
        # Calculate real flow
        flow = processor.calculate_optical_flow([prev_frame, curr_frame])
        print("Optical flow calculated from the last two frames.")
        
    else:
        # Static Image
        curr_frame = cv2.imread(args.image)
        if curr_frame is None:
            print(f"Error: Could not load image at {args.image}")
            return
            
        if curr_frame.shape[1] != 800 or curr_frame.shape[0] != 800:
            print(f"Resizing image from {curr_frame.shape[1]}x{curr_frame.shape[0]} to 800x800 using INTER_NEAREST")
            curr_frame = cv2.resize(curr_frame, (800, 800), interpolation=cv2.INTER_NEAREST)
            
        print(f"Loaded static image: {args.image} (Size: {curr_frame.shape[1]}x{curr_frame.shape[0]})")
        print(f"Simulated Wind Vector: ({args.vx}, {args.vy})")
        
        h, w = curr_frame.shape[:2]
        flow = np.zeros((h, w, 2), dtype=np.float32)
        flow[..., 0] = args.vx
        flow[..., 1] = args.vy
        prev_frame = curr_frame.copy()

    print(f"User Pixel Coordinate: ({px}, {py})")
    print(f"Testing Mode: {args.mode.upper()} LOGIC")
    
    # 3. Run the selected logic
    if args.mode == "old":
        clouds = find_approaching_clouds_old_logic(
            processor=processor,
            curr_frame=curr_frame,
            prev_frame=prev_frame,
            flow=flow,
            user_x=px,
            user_y=py,
            search_radius=80,
            min_dbz=20.0,
            cluster_dist=20
        )
    else:
        debug_img = curr_frame.copy()
        
        clouds = find_approaching_clouds_new_debug(
            processor=processor,
            curr_frame=curr_frame,
            prev_frame=prev_frame,
            flow=flow,
            user_x=px,
            user_y=py,
            search_radius=80,
            min_dbz=20.0,
            cluster_dist=20,
            hit_radius=args.hit_radius,
            debug_img=debug_img
        )
        
        # Save debug image
        cv2.circle(debug_img, (px, py), 3, (255, 0, 0), -1) # Blue dot for user
        cv2.circle(debug_img, (px, py), args.hit_radius, (255, 255, 255), 1) # White circle for hit radius
        cv2.imwrite("mock_test_debug_pixels.jpg", debug_img)
        print("Saved pixel-level debug image to mock_test_debug_pixels.jpg")
    
    print(f"\n--- LOGIC RESULTS ---")
    if not clouds:
        print("No approaching clouds detected. (Either no clouds nearby, or they are filtered out by trajectory/Cross Track Error)")
    else:
        print(f"Detected {len(clouds)} approaching clouds that will HIT the user:")
        for i, c in enumerate(clouds):
            print(f"  [{i+1}] dist={c['dist']:.1f}px, ETA={c['eta_min']:.1f}m, dbz={c['dbz_now']}")
        
    # 4. Generate the output visualization using production logic
    viz_bytes = processor.generate_radar_tracking_image(curr_frame, px, py, clouds)
    if viz_bytes:
        out_path = f"mock_test_result_{args.mode}.jpg"
        with open(out_path, "wb") as f:
            f.write(viz_bytes)
        print(f"\nSaved visualization to {out_path}")
    else:
        print("\nNo image generated by generate_radar_tracking_image(). (Likely clouds were outside crop area or filtered by ETA)")

if __name__ == "__main__":
    main()
