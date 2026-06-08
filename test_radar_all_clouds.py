import asyncio
import os
import cv2
import math
import sys

# Add backend to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.tmd_radar_processor import TMDRadarProcessor

async def main():
    processor = TMDRadarProcessor("kkn240")
    # Approx Udon Thani lat, lng
    lat, lng = 17.4138, 102.7872
    px, py = processor.latlng_to_pixel(lat, lng)
    if px is None:
        print("Out of bounds")
        return
        
    print(f"Fetching radar frames... user pixel is ({px}, {py})")
    frames, dt = await processor.fetch_loop_gif_and_extract_frames()
    if not frames:
        print("Failed to fetch frames")
        return
        
    # Run optical flow on all consecutive frames
    print("Processing frames and generating GIF...")
    import imageio
    
    out_frames = []
    # We need at least 2 frames for optical flow
    for i in range(1, len(frames)):
        curr_frame = frames[i]
        prev_frame = frames[i-1]
        
        flow = processor.calculate_optical_flow([prev_frame, curr_frame])
        
        search_radius = 80
        min_dbz = 20.0
        cluster_dist = 20
        
        candidates = []
        for dy in range(-search_radius, search_radius + 1, 2):
            for dx in range(-search_radius, search_radius + 1, 2):
                sx = px + dx
                sy = py + dy
                if not (0 <= sx < curr_frame.shape[1] and 0 <= sy < curr_frame.shape[0]):
                    continue
                d = processor.get_dbz_at_pixel(curr_frame, sx, sy)
                if d < min_dbz:
                    continue
                cvx, cvy = processor.get_flow_vector_at(flow, sx, sy)
                to_x = px - sx
                to_y = py - sy
                dist = math.sqrt(to_x ** 2 + to_y ** 2)
                if dist == 0:
                    continue
                    
                dot = (cvx * to_x + cvy * to_y) / dist
                d_prev = processor.get_dbz_at_pixel(prev_frame, int(round(sx - cvx)), int(round(sy - cvy)))
                candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))

        clusters = []
        used = [False] * len(candidates)
        for j, c in enumerate(candidates):
            if used[j]:
                continue
            group = [c]
            used[j] = True
            queue = [c]
            while queue:
                curr = queue.pop(0)
                for k, c2 in enumerate(candidates):
                    if not used[k] and math.sqrt((curr[0] - c2[0])**2 + (curr[1] - c2[1])**2) < cluster_dist:
                        group.append(c2)
                        used[k] = True
                        queue.append(c2)
                        
            total_w = sum(g[4] for g in group)
            cx = int(sum(g[0] * g[4] for g in group) / total_w)
            cy = int(sum(g[1] * g[4] for g in group) / total_w)
            avg_vx = sum(g[2] for g in group) / len(group)
            avg_vy = sum(g[3] for g in group) / len(group)
            dbz_now = max(g[4] for g in group)
            dbz_prev = max(g[5] for g in group)
            dist_c = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
            dot_c = sum(g[7] for g in group) / len(group)
            
            if abs(dot_c) < 0.1: dot_c = 0.1 if dot_c >= 0 else -0.1
            eta_min = (dist_c / dot_c) * 15.0
            
            clusters.append({
                "cx": cx, "cy": cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "dbz_prev": dbz_prev,
                "predicted_dbz": dbz_now,
                "dist": dist_c,
                "eta_min": eta_min,
            })
            
        img = curr_frame.copy()
        crop_r = 120
        h, w = img.shape[:2]
        x1, y1 = max(0, px - crop_r), max(0, py - crop_r)
        x2, y2 = min(w, px + crop_r), min(h, py + crop_r)
        crop_img = img[y1:y2, x1:x2].copy()
        
        scale = 3.0
        viz_img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        ux, uy = int((px - x1) * scale), int((py - y1) * scale)
        cv2.drawMarker(viz_img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(20 * scale), int(2 * scale))
        
        for c in clusters:
            cx_orig, cy_orig = c["cx"], c["cy"]
            if cx_orig < x1 - 50 or cx_orig > x2 + 50 or cy_orig < y1 - 50 or cy_orig > y2 + 50:
                continue
                
            cx_scaled, cy_scaled = int((cx_orig - x1) * scale), int((cy_orig - y1) * scale)
            dbz = c["dbz_now"]
            if dbz >= 50: color = (231, 76, 60)
            elif dbz >= 40: color = (243, 156, 18)
            elif dbz >= 30: color = (241, 196, 15)
            else: color = (46, 204, 113)
            
            cv2.circle(viz_img, (cx_scaled, cy_scaled), int(12 * scale), color, int(1.5 * scale))
            
            vx_scaled = int(c.get("vx", 0) * scale * 3.0)
            vy_scaled = int(c.get("vy", 0) * scale * 3.0)
            if vx_scaled != 0 or vy_scaled != 0:
                cv2.arrowedLine(viz_img, (cx_scaled, cy_scaled), (cx_scaled + vx_scaled, cy_scaled + vy_scaled), (255, 255, 0), int(1.5 * scale), tipLength=0.3)
                
            eta = c["eta_min"]
            label = f"AWAY {int(abs(eta))}m" if eta < 0 else f"ETA {int(eta)}m"
            cv2.putText(viz_img, label, (cx_scaled + int(15 * scale), cy_scaled), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale, (255, 255, 255), int(1.5 * scale))
            
        viz_rgb = cv2.cvtColor(viz_img, cv2.COLOR_BGR2RGB)
        out_frames.append(viz_rgb)

    out_path = os.path.join(os.path.dirname(__file__), "all_clouds.gif")
    imageio.mimsave(out_path, out_frames, fps=2)
    print(f"Saved GIF visualization to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
