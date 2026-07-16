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

    def extract_rain_mask(self, img: np.ndarray) -> np.ndarray:
        """Converts an RGB radar frame into a grayscale mask representing rain intensity."""
        img_float = img.astype(np.float32)
        
        min_dists = np.full(img.shape[:2], 25.0, dtype=np.float32)
        best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
        
        # Calculate min distance to any ignored color
        ignored_min_dists = np.full(img.shape[:2], float('inf'), dtype=np.float32)
        for ic in IGNORED_COLORS:
            ic_arr = np.array(ic, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - ic_arr)**2, axis=-1))
            better_mask = dist < ignored_min_dists
            ignored_min_dists[better_mask] = dist[better_mask]
            
        for color, dbz in DBZ_COLOR_MAPPING.items():
            c_arr = np.array(color, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
            
            # Must be closer to this dBZ color than to ANY ignored color
            valid_mask = dist < ignored_min_dists
            
            better_mask = (dist < min_dists) & valid_mask
            min_dists[better_mask] = dist[better_mask]
            
            intensity = int(min(255, max(50, dbz * 4)))
            best_intensity[better_mask] = intensity
            
        # Apply a small median blur to remove single-pixel noise which confuses optical flow
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
        min_dbz: float = 20.0,
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

        candidates = []
        dbz_pass = 0
        dot_pass = 0
        total_scanned = 0
        for dy in range(-search_radius, search_radius + 1, 2):
            for dx in range(-search_radius, search_radius + 1, 2):
                total_scanned += 1
                sx = user_x + dx
                sy = user_y + dy
                # Skip pixels outside the valid radar area (legend, borders)
                if not (valid_x_min <= sx < valid_x_max and valid_y_min <= sy < valid_y_max):
                    continue
                if not (0 <= sx < curr_frame.shape[1] and 0 <= sy < curr_frame.shape[0]):
                    continue
                d = self.get_dbz_at_pixel(curr_frame, sx, sy)
                if d < min_dbz:
                    continue
                dbz_pass += 1
                cvx, cvy = self.get_flow_vector_at(flow, sx, sy)
                to_x = user_x - sx
                to_y = user_y - sy
                dist = math.sqrt(to_x ** 2 + to_y ** 2)
                if dist == 0:
                    continue
                dot = (cvx * to_x + cvy * to_y) / dist
                # Only keep pixels whose flow APPROACHES the user (dot > dot_threshold)
                if dot <= dot_threshold:
                    continue
                dot_pass += 1
                
                v_mag = math.sqrt(cvx ** 2 + cvy ** 2)
                if v_mag < 0.1:
                    continue # Not moving enough to predict
                    
                # Perpendicular distance (Cross Track Error)
                perp_dist = abs(to_x * cvy - to_y * cvx) / v_mag
                if perp_dist > hit_radius:
                    continue
                # Previous DBZ at the backward-traced position
                prev_x = int(round(sx - cvx))
                prev_y = int(round(sy - cvy))
                d_prev = self.get_dbz_at_pixel(prev_frame, prev_x, prev_y) if prev_frame is not None else d
                candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))

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

    @staticmethod
    def get_all_rain_clusters(
        frame: np.ndarray,
        flow: np.ndarray,
        user_x: int,
        user_y: int,
        scan_radius: int = 200,
        min_dbz: float = 10.0,
        cluster_dist: int = 25,
    ) -> list:
        """
        Scan a wide radius for ALL rain clusters (regardless of direction).
        Returns a list of dicts with cx, cy, vx, vy, dbz_now, eta_min, approaching.
        Used for the always-visible radar overlay (circles + arrows).
        """
        from app.services.tmd_radar.processor import TMDRadarProcessor
        h, w = frame.shape[:2]
        candidates = []
        for dy in range(-scan_radius, scan_radius + 1, 1):
            for dx in range(-scan_radius, scan_radius + 1, 1):
                sx = user_x + dx
                sy = user_y + dy
                if sx < 0 or sx >= w or sy < 0 or sy >= h:
                    continue
                d = TMDRadarProcessor._get_dbz_at_pixel_static(frame, sx, sy)
                if d < min_dbz:
                    continue
                vx = float(flow[sy, sx, 0])
                vy = float(flow[sy, sx, 1])
                candidates.append((sx, sy, vx, vy, d))

        if not candidates:
            return []

        # Simple greedy clustering
        used = [False] * len(candidates)
        clusters = []
        for i, c1 in enumerate(candidates):
            if used[i]:
                continue
            group = [c1]
            used[i] = True
            queue = [c1]
            while queue:
                cur = queue.pop()
                for j, c2 in enumerate(candidates):
                    if used[j]:
                        continue
                    if math.hypot(cur[0] - c2[0], cur[1] - c2[1]) <= cluster_dist:
                        used[j] = True
                        group.append(c2)
                        queue.append(c2)

            total_w = sum(g[4] for g in group)
            if total_w <= 0:
                continue
            cx = int(sum(g[0] * g[4] for g in group) / total_w)
            cy = int(sum(g[1] * g[4] for g in group) / total_w)
            avg_vx = sum(g[2] for g in group) / len(group)
            avg_vy = sum(g[3] for g in group) / len(group)
            dbz_now = max(g[4] for g in group)

            v_mag = math.hypot(avg_vx, avg_vy)
            dist = math.hypot(cx - user_x, cy - user_y)

            # Determine if approaching
            approaching = False
            eta_min = None
            if v_mag > 0.1 and dist > 0:
                vx_norm = avg_vx / v_mag
                vy_norm = avg_vy / v_mag
                vec_x = user_x - cx
                vec_y = user_y - cy
                dot = vx_norm * (vec_x / dist) + vy_norm * (vec_y / dist)
                if dot > 0.3:  # looser than find_approaching_clouds threshold
                    approaching = True
                    eta_min = (dist / (v_mag * dot)) * 15.0

            if eta_min is None:
                eta_min = (dist / v_mag * 15.0) if v_mag > 0.1 else 9999.0

            xmin = min(g[0] for g in group)
            xmax = max(g[0] for g in group)
            ymin = min(g[1] for g in group)
            ymax = max(g[1] for g in group)

            clusters.append({
                "cx": cx, "cy": cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "predicted_dbz": dbz_now,
                "dist": dist,
                "eta_min": eta_min,
                "approaching": approaching,
                "size": len(group),
                "xmin": xmin, "xmax": xmax,
                "ymin": ymin, "ymax": ymax,
                "pixels": [(g[0], g[1]) for g in group]
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
