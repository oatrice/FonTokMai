import numpy as np
import cv2
import math
from app.services.tmd_radar.clustering import TMDClusteringMixin

class TMDClusteringSmallDilationMargin(TMDClusteringMixin):
    def extract_rain_mask(self, img: np.ndarray) -> np.ndarray:
        img_float = img.astype(np.float32)
        from app.services.tmd_radar_config import DBZ_COLOR_MAPPING, IGNORED_COLORS
        min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
        best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
        
        ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
        for ic in IGNORED_COLORS:
            ic_arr = np.array(ic, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
            better_mask = dist < ignored_min_dists
            ignored_min_dists[better_mask] = dist[better_mask]
            
        for color, dbz in DBZ_COLOR_MAPPING.items():
            c_arr = np.array(color, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
            valid_mask = dist < ignored_min_dists
            better_mask = (dist < min_dists) & valid_mask
            min_dists[better_mask] = dist[better_mask]
            intensity = int(min(255, max(50, dbz * 4)))
            best_intensity[better_mask] = intensity
            
        # Hysteresis with smaller dilation (15x15)
        weak_colors = [(87, 96, 65), (69, 78, 47), (130, 145, 106)]
        weak_mask = np.zeros(img.shape[:2], dtype=bool)
        for wc in weak_colors:
            wc_arr = np.array(wc, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - wc_arr)**2, axis=-1))
            weak_mask |= (dist < 15.0)
            
        if np.any(weak_mask):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            dilated_strong = cv2.dilate(best_intensity, kernel)
            valid_weak = weak_mask & (dilated_strong > 0)
            best_intensity[valid_weak] = max(50, int(15.0 * 4))
            
        return cv2.medianBlur(best_intensity, 3)

    def get_all_rain_clusters(
        self,
        frame: np.ndarray,
        flow: np.ndarray,
        user_x: int,
        user_y: int,
        scan_radius = None,
        min_dbz = 10.0,
        cluster_dist = 12,
        min_size = 5,
    ) -> list:
        h, w = frame.shape[:2]
        mask = self.extract_rain_mask(frame)
        min_intensity = int(min_dbz * 4)
        rain_pixels = mask >= min_intensity
        
        # Zero out the outer 80px margin
        rain_pixels[:80, :] = False
        rain_pixels[-80:, :] = False
        rain_pixels[:, :80] = False
        rain_pixels[:, -80:] = False

        y_coords, x_coords = np.nonzero(rain_pixels)
        if len(x_coords) == 0:
            return []
            
        bin_mask = (rain_pixels * 255).astype(np.uint8)
        ksize = cluster_dist
        if ksize % 2 == 0:
            ksize += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        closed_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        clusters = []
        for ctr in contours:
            x, y, cw, ch = cv2.boundingRect(ctr)
            local_bin = np.zeros((ch, cw), dtype=np.uint8)
            local_ctr = ctr - np.array([[[x, y]]], dtype=np.int32)
            cv2.fillPoly(local_bin, [local_ctr], 255)
            
            local_rain = rain_pixels[y:y+ch, x:x+cw]
            local_cluster = (local_bin > 0) & local_rain
            ly_coords, lx_coords = np.nonzero(local_cluster)
            
            if len(lx_coords) < min_size:
                continue
                
            cy_coords = ly_coords + y
            cx_coords = lx_coords + x
            
            pixel_intensities = mask[cy_coords, cx_coords]
            pixel_dbzs = pixel_intensities / 4.0
            
            pixel_vxs = flow[cy_coords, cx_coords, 0]
            pixel_vys = flow[cy_coords, cx_coords, 1]
            
            total_w = np.sum(pixel_dbzs)
            if total_w <= 0:
                continue
                
            cx = int(np.sum(cx_coords * pixel_dbzs) / total_w)
            cy = int(np.sum(cy_coords * pixel_dbzs) / total_w)
            avg_vx = float(np.mean(pixel_vxs))
            avg_vy = float(np.mean(pixel_vys))
            dbz_now = float(np.max(pixel_dbzs))
            
            max_idx = np.argmax(pixel_dbzs)
            peak_cx = int(cx_coords[max_idx])
            peak_cy = int(cy_coords[max_idx])
            
            v_mag = math.hypot(avg_vx, avg_vy)
            dist = math.hypot(cx - user_x, cy - user_y)
            
            approaching = False
            eta_min = None
            if v_mag > 0.1 and dist > 0:
                vx_norm = avg_vx / v_mag
                vy_norm = avg_vy / v_mag
                vec_x = user_x - cx
                vec_y = user_y - cy
                dot = vx_norm * (vec_x / dist) + vy_norm * (vec_y / dist)
                if dot > 0.3:
                    approaching = True
                    eta_min = (dist / (v_mag * dot)) * 15.0
                    
            if eta_min is None:
                eta_min = (dist / v_mag * 15.0) if v_mag > 0.1 else 9999.0
                
            xmin, xmax = int(np.min(cx_coords)), int(np.max(cx_coords))
            ymin, ymax = int(np.min(cy_coords)), int(np.max(cy_coords))
            
            clusters.append({
                "cx": cx, "cy": cy,
                "peak_cx": peak_cx, "peak_cy": peak_cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "predicted_dbz": dbz_now,
                "dist": dist,
                "eta_min": eta_min,
                "approaching": approaching,
                "size": len(cx_coords),
                "bbox": (xmin, xmax, ymin, ymax),
                "xmin": xmin, "xmax": xmax,
                "ymin": ymin, "ymax": ymax,
                "pixels": list(zip(map(int, cx_coords), map(int, cy_coords)))
            })
            
        return clusters

data = np.load('backend/tests/test_kkn240_frames.npz')
frames = data['frames']
img = frames[-1]
flow = data['flow']

cls = TMDClusteringSmallDilationMargin()
clusters = cls.get_all_rain_clusters(img, flow, 486, 390)
print("WITH 15x15 DILATION AND MARGIN:")
for c in clusters:
    if c['size'] > 1000:
        print(f"Cluster: cx={c['cx']}, cy={c['cy']}, size={c['size']}, dbz={c['dbz_now']}, bbox={c['xmin']}-{c['xmax']}, {c['ymin']}-{c['ymax']}")
