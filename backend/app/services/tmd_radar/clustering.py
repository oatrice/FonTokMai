import os
import asyncio
import time
import logging
import math
import io
import re
import cv2
import httpx
import numpy as np
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from zoneinfo import ZoneInfo
from typing import List, Tuple, Optional
from app.dependencies import get_repo_context
from app.services.ocr_service import OCRService
from google.cloud import storage
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS

logger = logging.getLogger(__name__)


def _load_thai_font(size: int) -> "ImageFont.FreeTypeFont":
    """Return the best available font that supports Thai characters.

    Priority order (Thai-capable → Latin fallbacks → PIL default):
      macOS  : Tahoma, Arial Unicode MS
      Linux  : Noto Sans Thai, Garuda, LiberationSans, DejaVu Sans
    """
    candidates = [
        # macOS Thai fonts
        "/System/Library/Fonts/Supplemental/Thonburi.ttc",
        "/System/Library/Fonts/ThonburiUI.ttc",
        "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
        "/System/Library/Fonts/Supplemental/Sathu.ttf",
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/Library/Fonts/Tahoma.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux / Docker Thai fonts (install fonts-thai-tlwg or fonts-noto-core)
        "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/tlwg/Loma.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/Garuda.ttf",
        "/usr/share/fonts/truetype/thai-tlwg/Loma.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        # Generic Latin fallbacks
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


class TMDClusteringMixin:

    def get_dbz_at_pixel(self, img: np.ndarray, x: int, y: int) -> float:
        """Reads the color at (x,y) and returns the corresponding dBZ value.
        
        Frames are in RGB format (from PIL). DBZ_COLOR_MAPPING keys are RGB tuples.
        """
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return 0.0
            
        # Frames from PIL are RGB: pixel[0]=R, pixel[1]=G, pixel[2]=B
        pixel = img[y, x]
        if len(pixel) >= 3:
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        else:
            return 0.0
            
        color_tuple = (r, g, b)
        
        # Check ignored colors first (distance)
        min_dist_ignored = float('inf')
        for ic in IGNORED_COLORS:
            dist = math.sqrt((r - ic[0])**2 + (g - ic[1])**2 + (b - ic[2])**2)
            if dist < min_dist_ignored:
                min_dist_ignored = dist
        
        # Find nearest dBZ color
        min_dist_dbz = float('inf')
        best_dbz = 0.0
        
        for known_color, dbz in DBZ_COLOR_MAPPING.items():
            dist = math.sqrt((r - known_color[0])**2 + (g - known_color[1])**2 + (b - known_color[2])**2)
            if dist < min_dist_dbz:
                min_dist_dbz = dist
                best_dbz = dbz
                
        # If it's mathematically closer to a background color, it's noise
        if min_dist_ignored <= min_dist_dbz:
            return 0.0
            
        # Tighter threshold (25) reduces false positives from map features while allowing JPEG artifact tolerance
        if min_dist_dbz < 25:
            return best_dbz
            
        return 0.0
    @staticmethod
    def _get_dbz_at_pixel_static(img: np.ndarray, x: int, y: int) -> float:
        """Static version of get_dbz_at_pixel for use in classmethod/staticmethod context."""
        pixel = img[y, x]
        r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        min_dist_dbz = float('inf')
        best_dbz = 0.0
        min_dist_ignored = float('inf')

        for color, dbz in DBZ_COLOR_MAPPING.items():
            dist = math.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
            if dist < min_dist_dbz:
                min_dist_dbz = dist
                best_dbz = dbz

        for ic in IGNORED_COLORS:
            dist = math.sqrt((r - ic[0])**2 + (g - ic[1])**2 + (b - ic[2])**2)
            if dist < min_dist_ignored:
                min_dist_ignored = dist

        if min_dist_ignored <= min_dist_dbz:
            return 0.0
        if min_dist_dbz < 25:
            return best_dbz
        return 0.0

    def _extract_raw_dbz_map(self, img: np.ndarray) -> np.ndarray:
        """Vectorized dBZ intensity map WITHOUT medianBlur.

        Use this for per-pixel candidate detection (find_approaching_clouds)
        where we need every individual rain pixel.
        ``extract_rain_mask`` applies medianBlur which eliminates sparse/isolated
        pixels and is intended only for optical-flow computation.
        """
        from app.services.weather_manager import _DEV_CONFIG
        enable_hsv = _DEV_CONFIG.get("enable_hsv_mask", True)

        img_float = img.astype(np.float32)
        best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)

        if enable_hsv:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            lower_hsv1 = np.array([0, 160, 130], dtype=np.uint8)
            upper_hsv1 = np.array([180, 255, 255], dtype=np.uint8)
            hsv_mask = cv2.inRange(hsv, lower_hsv1, upper_hsv1)
            
            ignore_mask = np.zeros(img.shape[:2], dtype=bool)
            for ic in IGNORED_COLORS:
                ic_arr = np.array(ic, dtype=np.float32)
                dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
                ignore_mask |= (dist < 18.0)
            
            hsv_mask[ignore_mask] = 0
            best_intensity[hsv_mask > 0] = max(50, int(15.0 * 4))

        min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
        ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
        for ic in IGNORED_COLORS:
            ic_arr = np.array(ic, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - ic_arr) ** 2, axis=-1))
            better = dist < ignored_min_dists
            ignored_min_dists[better] = dist[better]

        for color, dbz in DBZ_COLOR_MAPPING.items():
            c_arr = np.array(color, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - c_arr) ** 2, axis=-1))
            valid = dist < ignored_min_dists
            better = (dist < min_dists) & valid
            min_dists[better] = dist[better]
            intensity = int(min(255, max(50, dbz * 4)))
            best_intensity[better] = intensity

        # Return raw intensity map (no medianBlur) — float32 dBZ approximation
        return best_intensity.astype(np.float32) / 4.0

    def extract_rain_mask(self, img: np.ndarray) -> np.ndarray:
        """Converts an RGB radar frame into a grayscale mask representing rain intensity.

        Applies medianBlur to remove single-pixel noise — use this for optical flow.
        For per-pixel candidate detection, use _extract_raw_dbz_map() instead.
        """
        from app.services.weather_manager import _DEV_CONFIG
        enable_hsv = _DEV_CONFIG.get("enable_hsv_mask", True)

        img_float = img.astype(np.float32)
        best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)

        if enable_hsv:
            # Convert RGB to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            # Define broad range that matches radar storm pixels:
            # Hue: 0-180 (all colors), Saturation: 90-255 (vibrant colors), Value: 100-255 (bright colors)
            lower_hsv1 = np.array([0, 160, 130], dtype=np.uint8)
            upper_hsv1 = np.array([180, 255, 255], dtype=np.uint8)
            hsv_mask = cv2.inRange(hsv, lower_hsv1, upper_hsv1)
            
            # Map background / ignore colors specifically (terrain greens/grays/blues that could blend in)
            ignore_mask = np.zeros(img.shape[:2], dtype=bool)
            for ic in IGNORED_COLORS:
                ic_arr = np.array(ic, dtype=np.float32)
                dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
                ignore_mask |= (dist < 18.0)
            
            # Remove ignored background map features from the HSV mask
            hsv_mask[ignore_mask] = 0
            
            # Set default intensity for valid storm pixels
            best_intensity[hsv_mask > 0] = max(50, int(15.0 * 4)) # default 15 dBZ

        # Fallback and exact match reinforcement from standard RGB DBZ Color Mapping
        min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
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
            
        # Hysteresis for faded rain edges (which mix with map background)
        weak_colors = [(87, 96, 65), (69, 78, 47), (130, 145, 106)]
        weak_mask = np.zeros(img.shape[:2], dtype=bool)
        for wc in weak_colors:
            wc_arr = np.array(wc, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - wc_arr)**2, axis=-1))
            weak_mask |= (dist < 15.0)
        if np.any(weak_mask):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated_strong = cv2.dilate(best_intensity, kernel)
            valid_weak = weak_mask & (dilated_strong > 0)
            best_intensity[valid_weak] = max(50, int(15.0 * 4))
            
        # Apply a small median blur to remove single-pixel noise
        mask = cv2.medianBlur(best_intensity, 3)
        return mask

    def find_approaching_clouds(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
        flow: np.ndarray,
        user_x: int,
        user_y: int,
        search_radius: int = 80,
        min_dbz: float = 10.0,
        cluster_dist: int = 20,
        hit_radius: int = 20,
        cluster_min: int = 3,
        dot_threshold: float = 0.5,
    ) -> list:
        """
        Scans all rain pixels within search_radius of (user_x, user_y).
        Keeps only pixels whose flow vector points TOWARD the user (dot product > 0).
        Clusters nearby pixels (weighted by dBZ) into distinct cloud groups.
        Returns a list of dicts sorted by ETA (soonest first), each containing:
          cx, cy, dbz_now, dbz_prev, growth_rate, predicted_dbz, dist, eta_min
        """
        # Restrict search to the valid radar crop area to exclude legend strips
        is_loop = flow.shape[0] < 800 or flow.shape[1] < 800
        crop_x0 = self.config.loop_crop_x if is_loop else self.config.static_crop_x
        crop_y0 = self.config.loop_crop_y if is_loop else self.config.static_crop_y
        crop_w  = self.config.loop_crop_width if is_loop else self.config.static_crop_width
        crop_h  = self.config.loop_crop_height if is_loop else self.config.static_crop_height
        valid_x_min = crop_x0
        valid_x_max = crop_x0 + crop_w
        valid_y_min = crop_y0
        valid_y_max = crop_y0 + crop_h

        H, W = curr_frame.shape[:2]

        # ── Vectorized candidate extraction ──────────────────────────────────
        # Build a grid of all (sx, sy) offsets inside search_radius, step=1.
        # Step 1 (vs old step 2) gives finer coverage with no extra Python loop.
        ys_off = np.arange(-search_radius, search_radius + 1, dtype=np.int32)
        xs_off = np.arange(-search_radius, search_radius + 1, dtype=np.int32)
        grid_dy, grid_dx = np.meshgrid(ys_off, xs_off, indexing="ij")

        sx_all = user_x + grid_dx            # shape (2R+1, 2R+1)
        sy_all = user_y + grid_dy

        # Mask 1: within frame bounds
        in_frame = (sx_all >= 0) & (sx_all < W) & (sy_all >= 0) & (sy_all < H)
        # Mask 2: within valid crop area
        in_crop = (
            (sx_all >= valid_x_min) & (sx_all < valid_x_max) &
            (sy_all >= valid_y_min) & (sy_all < valid_y_max)
        )
        valid_mask = in_frame & in_crop

        # Use raw dBZ map (no medianBlur) so isolated rain pixels are not erased.
        # extract_rain_mask() applies medianBlur which is correct for optical flow
        # but would eliminate sparse candidate pixels before clustering.
        dbz_full = self._extract_raw_dbz_map(curr_frame)   # float32 dBZ per pixel

        # Safe clamped indices for array lookup — out-of-bounds pixels are
        # excluded by valid_mask already, but numpy requires non-negative indices.
        sx_safe = np.clip(sx_all, 0, W - 1)
        sy_safe = np.clip(sy_all, 0, H - 1)
        dbz_at_grid = dbz_full[sy_safe, sx_safe]          # safe everywhere; invalid pixels filtered by valid_mask
        dbz_mask = valid_mask & (dbz_at_grid >= min_dbz)

        # Extract flow vectors at all candidate pixels (vectorized)
        sx_cands = sx_all[dbz_mask]
        sy_cands = sy_all[dbz_mask]
        dbz_cands = dbz_at_grid[dbz_mask]

        # Flow at candidate positions
        cvx_arr = flow[sy_cands, sx_cands, 0]
        cvy_arr = flow[sy_cands, sx_cands, 1]

        # Vector from pixel to user
        to_x_arr = (user_x - sx_cands).astype(np.float32)
        to_y_arr = (user_y - sy_cands).astype(np.float32)
        dist_arr = np.sqrt(to_x_arr ** 2 + to_y_arr ** 2)

        # Avoid division by zero
        nonzero = dist_arr > 0
        sx_cands  = sx_cands[nonzero]
        sy_cands  = sy_cands[nonzero]
        dbz_cands = dbz_cands[nonzero]
        cvx_arr   = cvx_arr[nonzero]
        cvy_arr   = cvy_arr[nonzero]
        to_x_arr  = to_x_arr[nonzero]
        to_y_arr  = to_y_arr[nonzero]
        dist_arr  = dist_arr[nonzero]

        # Dot product filter: flow must point TOWARD user
        dot_arr = (cvx_arr * to_x_arr + cvy_arr * to_y_arr) / dist_arr
        approach_mask = dot_arr > dot_threshold
        sx_cands  = sx_cands[approach_mask]
        sy_cands  = sy_cands[approach_mask]
        dbz_cands = dbz_cands[approach_mask]
        cvx_arr   = cvx_arr[approach_mask]
        cvy_arr   = cvy_arr[approach_mask]
        to_x_arr  = to_x_arr[approach_mask]
        to_y_arr  = to_y_arr[approach_mask]
        dist_arr  = dist_arr[approach_mask]
        dot_arr   = dot_arr[approach_mask]

        # Speed filter: must be moving
        v_mag_arr = np.sqrt(cvx_arr ** 2 + cvy_arr ** 2)
        moving_mask = v_mag_arr >= 0.1
        sx_cands  = sx_cands[moving_mask]
        sy_cands  = sy_cands[moving_mask]
        dbz_cands = dbz_cands[moving_mask]
        cvx_arr   = cvx_arr[moving_mask]
        cvy_arr   = cvy_arr[moving_mask]
        to_x_arr  = to_x_arr[moving_mask]
        to_y_arr  = to_y_arr[moving_mask]
        dist_arr  = dist_arr[moving_mask]
        dot_arr   = dot_arr[moving_mask]
        v_mag_arr = v_mag_arr[moving_mask]

        # Cross-track error filter (perpendicular distance)
        perp_arr = np.abs(to_x_arr * cvy_arr - to_y_arr * cvx_arr) / v_mag_arr
        hit_mask = perp_arr <= hit_radius
        sx_cands  = sx_cands[hit_mask]
        sy_cands  = sy_cands[hit_mask]
        dbz_cands = dbz_cands[hit_mask]
        cvx_arr   = cvx_arr[hit_mask]
        cvy_arr   = cvy_arr[hit_mask]
        dist_arr  = dist_arr[hit_mask]
        dot_arr   = dot_arr[hit_mask]

        # Prev-frame dBZ (still per-candidate, but candidates are now few)
        prev_dbz_full = self._extract_raw_dbz_map(prev_frame) if prev_frame is not None else None
        if prev_dbz_full is not None:
            prev_sx = np.clip(np.round(sx_cands - cvx_arr).astype(np.int32), 0, W - 1)
            prev_sy = np.clip(np.round(sy_cands - cvy_arr).astype(np.int32), 0, H - 1)
            dbz_prev_arr = prev_dbz_full[prev_sy, prev_sx]
        else:
            dbz_prev_arr = dbz_cands.copy()

        total_scanned = (2 * search_radius + 1) ** 2
        dbz_pass  = int(np.count_nonzero(dbz_at_grid[valid_mask] >= min_dbz))
        dot_pass  = len(sx_cands)
        candidates = list(zip(
            sx_cands.tolist(), sy_cands.tolist(),
            cvx_arr.tolist(), cvy_arr.tolist(),
            dbz_cands.tolist(), dbz_prev_arr.tolist(),
            dist_arr.tolist(), dot_arr.tolist(),
        ))
        # ─────────────────────────────────────────────────────────────────────

        logger.info(
            f"[DEBUG_APPROACH] user_x={user_x}, user_y={user_y}, min_dbz={min_dbz}, "
            f"scanned={total_scanned}, dbz_pass={dbz_pass}, dot_pass={dot_pass}, "
            f"candidates={len(candidates)}"
        )

        if not candidates:
            return []

        clusters = []
        used = [False] * len(candidates)
        for i, c in enumerate(candidates):
            if used[i]:
                continue
            group = [c]
            used[i] = True
            
            # Use BFS to find all connected pixels (Connected Components)
            queue = [c]
            while queue:
                curr = queue.pop(0)
                for j, c2 in enumerate(candidates):
                    if not used[j]:
                        if math.sqrt((curr[0] - c2[0]) ** 2 + (curr[1] - c2[1]) ** 2) < cluster_dist:
                            group.append(c2)
                            used[j] = True
                            queue.append(c2)

            if len(group) < cluster_min:
                continue

            total_w = sum(g[4] for g in group)
            cx = int(sum(g[0] * g[4] for g in group) / total_w)
            cy = int(sum(g[1] * g[4] for g in group) / total_w)
            avg_vx = sum(g[2] for g in group) / len(group)
            avg_vy = sum(g[3] for g in group) / len(group)
            dbz_now  = max(g[4] for g in group)
            dbz_prev = max(g[5] for g in group)
            dist_c   = math.sqrt((cx - user_x) ** 2 + (cy - user_y) ** 2)
            dot_c    = sum(g[7] for g in group) / len(group)
            
            # Avoid division by zero
            if abs(dot_c) < 0.1:
                dot_c = 0.1 if dot_c >= 0 else -0.1
                
            eta_min  = (dist_c / dot_c) * 15.0

            growth_rate   = (dbz_now - dbz_prev) / dbz_prev if dbz_prev > 0 else 0.0
            
            # Predict future intensity only if incoming, otherwise use current
            eta_steps = max(0.0, eta_min / 15.0)
            
            from app.services.weather_manager import _DEV_CONFIG
            if _DEV_CONFIG.get("decay_enabled", True):
                predicted_dbz = max(0.0, min(75.0, dbz_now * ((1 + growth_rate) ** eta_steps)))
            else:
                predicted_dbz = dbz_now

            clusters.append({
                "cx": cx, "cy": cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "dbz_prev": dbz_prev,
                "growth_rate": growth_rate,
                "predicted_dbz": predicted_dbz,
                "dist": dist_c,
                "eta_min": eta_min,
                "pixels": [(g[0], g[1]) for g in group],
                "approaching": True
            })

        clusters.sort(key=lambda c: c["eta_min"])
        return clusters

    def get_all_rain_clusters(
        self,
        frame: np.ndarray,
        flow: np.ndarray,
        user_x: int,
        user_y: int,
        scan_radius: Optional[int] = None,
        min_dbz: float = 10.0,
        cluster_dist: int = 12,
        min_size: int = 5,
    ) -> list:
        """
        Scan for ALL rain clusters (regardless of direction).
        Uses OpenCV contour detection for massive speedup over Python loops.
        """
        h, w = frame.shape[:2]
        
        # 1. Get intensity mask for whole image
        # extract_rain_mask returns uint8 with intensity = min(255, dbz * 4)
        mask = TMDClusteringMixin.extract_rain_mask(None, frame)
        
        # 2. Filter by min_dbz
        min_intensity = int(min_dbz * 4)
        rain_pixels = mask >= min_intensity
        
        # Circular Mask: Clip valid rain pixels to inside the radar's circular range ring
        center_x = self.config.loop_crop_width / 2.0 + self.config.loop_crop_x
        center_y = self.config.loop_crop_height / 2.0 + self.config.loop_crop_y
        pixel_radius = self.config.loop_crop_width / 2.0
        
        Y, X = np.ogrid[:h, :w]
        dist_from_center_sq = (X - center_x)**2 + (Y - center_y)**2
        outside_circle = dist_from_center_sq > (pixel_radius - 2)**2
        rain_pixels[outside_circle] = False
        
        # Zero out the legend/colorbar bounding boxes
        if getattr(self.config, "legend_bboxes", None):
            for (lx1, ly1, lx2, ly2) in self.config.legend_bboxes:
                lx1_c = max(0, min(w, lx1))
                ly1_c = max(0, min(h, ly1))
                lx2_c = max(0, min(w, lx2))
                ly2_c = max(0, min(h, ly2))
                rain_pixels[ly1_c:ly2_c, lx1_c:lx2_c] = False
        
        if scan_radius is not None:
            roi_mask = np.zeros_like(mask)
            x1, y1 = max(0, user_x - scan_radius), max(0, user_y - scan_radius)
            x2, y2 = min(w, user_x + scan_radius + 1), min(h, user_y + scan_radius + 1)
            roi_mask[y1:y2, x1:x2] = 1
            rain_pixels = rain_pixels & (roi_mask > 0)
            
        y_coords, x_coords = np.nonzero(rain_pixels)
        if len(x_coords) == 0:
            return []
            
        # 3. Morphological close to bridge gaps of `cluster_dist`
        bin_mask = (rain_pixels * 255).astype(np.uint8)
        ksize = cluster_dist
        if ksize % 2 == 0:
            ksize += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        closed_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
        
        # Check connected components before and after MORPH_CLOSE
        from app.services.weather_manager import _DEV_CONFIG
        if _DEV_CONFIG.get("verbose"):
            num_labels_before, _ = cv2.connectedComponents(bin_mask)
            num_labels_after, _ = cv2.connectedComponents(closed_mask)
            print(
                f"[DEBUG_CLUSTERING] get_all_rain_clusters: cluster_dist={cluster_dist}, "
                f"connected components before={num_labels_before}, after={num_labels_after}"
            )
        
        # 4. Find contours
        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        clusters = []
        for ctr in contours:
            # Mask just this contour
            x, y, cw, ch = cv2.boundingRect(ctr)
            # Create a small local mask for speed
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
            
        clusters.sort(key=lambda c: c["dist"])
        for i, c in enumerate(clusters):
            c["label"] = chr(ord('A') + min(i, 25))
        return clusters

    def calculate_growth_decay(self, prev_img: np.ndarray, curr_img: np.ndarray, x: int, y: int, radius: int = 10) -> float:
        """
        Calculates the growth or decay percentage of a rain cell around (x, y).
        Positive = Growth (Formation / Intensification)
        Negative = Decay (Dissipation / Weakening)
        
        It compares the sum of dBZ values in the region between the two frames.
        """
        prev_sum = 0.0
        curr_sum = 0.0
        count = 0
        
        # Look at a bounding box around (x,y)
        x_start = max(0, x - radius)
        x_end = min(curr_img.shape[1], x + radius)
        y_start = max(0, y - radius)
        y_end = min(curr_img.shape[0], y + radius)
        
        for iy in range(y_start, y_end):
            for ix in range(x_start, x_end):
                dbz_prev = self.get_dbz_at_pixel(prev_img, ix, iy)
                dbz_curr = self.get_dbz_at_pixel(curr_img, ix, iy)
                prev_sum += dbz_prev
                curr_sum += dbz_curr
                count += 1
                
        if count == 0:
            return 0.0
            
        if prev_sum == 0 and curr_sum == 0:
            return 0.0
        elif prev_sum == 0 and curr_sum > 0:
            return 100.0 # Formed from nothing
        elif prev_sum > 0 and curr_sum == 0:
            return -100.0 # Dissipated completely
            
        percent_change = ((curr_sum - prev_sum) / prev_sum) * 100.0
        return percent_change

    def _get_max_dbz_in_radius(self, img: np.ndarray, x: int, y: int, radius: int = 5) -> float:
        max_dbz = 0.0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = x + dx
                sy = y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = self.get_dbz_at_pixel(img, sx, sy)
                    if d > max_dbz:
                        max_dbz = d
        return max_dbz

    def get_wind_speed_kmh_from_vector(self, vx: float, vy: float) -> float:
        pixel_speed_15m = math.sqrt(vx**2 + vy**2)
        
        # Calculate km per pixel (approx 1 degree = 111 km)
        lon_diff = self.config.bbox.lng_max - self.config.bbox.lng_min
        width_km = lon_diff * 111.0
        km_per_pixel = width_km / max(1, self.config.loop_crop_width)
        
        km_per_15m = pixel_speed_15m * km_per_pixel
        km_per_h = km_per_15m * 4.0
        
        return float(km_per_h)

    def get_wind_speed_kmh(self, flow: np.ndarray, px: int, py: int) -> float:
        """
        Converts the optical flow vector (px/15min) into wind speed (km/h) 
        based on the geographic bounding box size.
        """
        vx, vy = self.get_flow_vector_at(flow, px, py)
        return self.get_wind_speed_kmh_from_vector(vx, vy)

    def get_wind_direction_text_from_vector(self, vx: float, vy: float) -> str:
        if abs(vx) < 0.5 and abs(vy) < 0.5:
            return "ไม่ทราบ"
            
        # Map image vector to standard compass heading (North=0, East=90, South=180, West=270)
        # In image coords: North is vy < 0. East is vx > 0.
        # math.atan2(y, x): using vx as y and -vy as x gives:
        # North (vx=0, vy=-1) -> atan2(0, 1) = 0 deg
        # East (vx=1, vy=0) -> atan2(1, 0) = 90 deg
        # Wind direction for radar should be where it's heading TO (for easier user understanding)
        # instead of the meteorological standard (where it's coming FROM)
        to_angle = math.degrees(math.atan2(vx, -vy)) % 360
        
        # Convert to 16 compass points
        val = int((to_angle / 22.5) + .5)
        arr = ["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        return f"{arr[(val % 16)]} ({int(to_angle)}°)"

    def get_wind_direction_text(self, flow: np.ndarray, px: int, py: int) -> str:
        vx, vy = self.get_flow_vector_at(flow, px, py)
        return self.get_wind_direction_text_from_vector(vx, vy)
