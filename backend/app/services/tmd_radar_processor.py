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
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/Library/Fonts/Tahoma.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux / Docker Thai fonts (install fonts-thai-tlwg or fonts-noto-core)
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

class TMDRadarProcessor:
    def __init__(self, station_code: str):
        self.station_code = station_code
        if station_code not in STATIONS:
            raise ValueError(f"Unknown station code: {station_code}")
        self.config = STATIONS[station_code]
        self.storage_dir = os.path.join(os.getcwd(), "backend", "tmp")

    def latlng_to_pixel(self, lat: float, lng: float, is_loop: bool = True, projection: str = None) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box."""
        bbox = self.config.bbox
        if lat > bbox.lat_max or lat < bbox.lat_min or lng < bbox.lng_min or lng > bbox.lng_max:
            return None, None
            
        # Use config's projection if not explicitly provided
        if projection is None:
            projection = getattr(self.config, 'projection_type', 'linear')
            
        # Select crop parameters based on image type
        crop_x = self.config.loop_crop_x if is_loop else self.config.static_crop_x
        crop_y = self.config.loop_crop_y if is_loop else self.config.static_crop_y
        crop_width = self.config.loop_crop_width if is_loop else self.config.static_crop_width
        crop_height = self.config.loop_crop_height if is_loop else self.config.static_crop_height
        
        if projection == "azimuthal" and hasattr(self.config, 'center_lat') and self.config.radius_km > 0:
            # Haversine distance
            R = 6371.0 # Earth radius in km
            lat1 = math.radians(self.config.center_lat)
            lon1 = math.radians(self.config.center_lng)
            lat2 = math.radians(lat)
            lon2 = math.radians(lng)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance_km = R * c
            
            # Bearing
            y = math.sin(dlon) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
            bearing = math.atan2(y, x)
            
            # Pixel mapping (center of crop area is center of radar)
            pixel_radius = crop_width / 2.0
            r_px = (distance_km / self.config.radius_km) * pixel_radius
            
            # Note: bearing is from North (0), rotating clockwise.
            # In image coordinates, y goes down.
            dx = r_px * math.sin(bearing)
            dy = -r_px * math.cos(bearing)
            
            # Center of the crop area
            center_x = crop_width / 2.0
            center_y = crop_height / 2.0
            
            px = int(center_x + dx) + crop_x
            py = int(center_y + dy) + crop_y
            return px, py
        else:
            # Fallback to standard linear interpolation using bounding box (Flat)
            x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
            y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)
            
            # Crop offsets
            px = int(x_pct * crop_width) + crop_x
            py = int(y_pct * crop_height) + crop_y
            return px, py

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

    def densify_optical_flow(self, flow: np.ndarray) -> np.ndarray:
        """
        Interpolates optical flow vectors from cloudy regions into empty regions 
        using Normalized Convolution.
        """
        # Calculate magnitude of flow vectors
        mag = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        
        # Create a mask where flow is significant (e.g. moving more than 0.1 pixels)
        mask = (mag > 0.1).astype(np.float32)
        
        if np.sum(mask) < 10:
            return flow  # Too little movement to extrapolate safely
            
        # Global average of valid flow vectors
        global_dx = np.sum(flow[..., 0] * mask) / np.sum(mask)
        global_dy = np.sum(flow[..., 1] * mask) / np.sum(mask)
        
        # 1. Mask the flow
        flow_masked = flow * mask[..., np.newaxis]
        
        # 2. Blur the masked flow and the mask (large kernel to spread wind widely)
        ksize = (101, 101)
        flow_blurred = cv2.blur(flow_masked, ksize)
        mask_blurred = cv2.blur(mask, ksize)
        
        # 3. Divide to get local average (Normalized Convolution)
        mask_blurred_expanded = mask_blurred[..., np.newaxis]
        valid_areas = mask_blurred_expanded > 0.001
        
        dense_flow = np.zeros_like(flow)
        
        # Where blur reached, use local average. Otherwise use global average.
        dense_flow = np.where(
            valid_areas, 
            flow_blurred / (mask_blurred_expanded + 1e-6), 
            np.array([global_dx, global_dy], dtype=np.float32)
        )
        
        # Blend original flow where we had confident data
        dense_flow = np.where(mask[..., np.newaxis] > 0, flow, dense_flow)
        
        return dense_flow

    def calculate_optical_flow(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Calculates dense optical flow using Farneback algorithm between the last two frames.
        Frames must be isolated for rain to prevent the map background from anchoring the flow.
        """
        if len(frames) < 2:
            raise ValueError("At least 2 frames required for optical flow")
            
        prev_img = frames[-2]
        curr_img = frames[-1]
        
        # Isolate the rain pixels into a grayscale intensity map
        prev_gray = self.extract_rain_mask(prev_img)
        curr_gray = self.extract_rain_mask(curr_img)
            
        # Calculate dense optical flow by Farneback method
        # flow[y, x, 0] = dx
        # flow[y, x, 1] = dy
        flow = cv2.calcOpticalFlowFarneback(
            prev=prev_gray,
            next=curr_gray,
            flow=None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        # Extrapolate wind into empty regions so tracking works everywhere
        flow = self.densify_optical_flow(flow)
        
        return flow
        
    def generate_flow_debug_images(self, prev_img: np.ndarray, curr_img: np.ndarray, flow: np.ndarray, clusters: list) -> dict:
        """
        Generates debug images for optical flow analysis:
        1. Rain Mask
        2. HSV Heatmap
        3. Flow Grid
        4. Clusters
        """
        images = {}
        
        # 1. Rain Mask
        curr_gray = self.extract_rain_mask(curr_img)
        is_success, buffer = cv2.imencode(".png", curr_gray)
        if is_success:
            images["rain_mask"] = buffer.tobytes()
            
        # 2. HSV Heatmap
        hsv = np.zeros((flow.shape[0], flow.shape[1], 3), dtype=np.uint8)
        hsv[..., 1] = 255
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv[..., 0] = ang * 180 / np.pi / 2
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
        bgr_flow = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        is_success, buffer = cv2.imencode(".png", bgr_flow)
        if is_success:
            images["flow_hsv"] = buffer.tobytes()
            
        # 3. Flow Vector Grid
        # Create a copy and ensure it's BGR for imencode if it's RGB
        # If curr_img is RGB, cvtColor is needed later. Let's assume it's RGB.
        grid_img = curr_img.copy()
        step = 16
        h, w = curr_img.shape[:2]
        y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
        fx, fy = flow[y,x].T
        lines = np.vstack([x, y, x+fx*3, y+fy*3]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        cv2.polylines(grid_img, lines, 0, (0, 255, 0), 1)
        for (x1, y1), (_x2, _y2) in lines:
            cv2.circle(grid_img, (x1, y1), 1, (0, 255, 0), -1)
        is_success, buffer = cv2.imencode(".png", cv2.cvtColor(grid_img, cv2.COLOR_RGB2BGR))
        if is_success:
            images["flow_grid"] = buffer.tobytes()
            
        # 4. Cluster Averages
        cluster_img = curr_img.copy()
        for c in clusters:
            cx, cy = c["cx"], c["cy"]
            vx, vy = c["vx"], c["vy"]
            size = c.get("size", 10)
            r = int(math.sqrt(size) * 1.5)
            cv2.rectangle(cluster_img, (cx - r, cy - r), (cx + r, cy + r), (255, 0, 255), 1)
            cv2.arrowedLine(cluster_img, (cx, cy), (int(cx + vx*3), int(cy + vy*3)), (255, 255, 0), 2, tipLength=0.3)
            
        is_success, buffer = cv2.imencode(".png", cv2.cvtColor(cluster_img, cv2.COLOR_RGB2BGR))
        if is_success:
            images["clusters"] = buffer.tobytes()
            
        return images
        
    def generate_multiframe_flow_debug_images(self, frames: List[np.ndarray], user_px: int, user_py: int, min_dbz: float) -> dict:
        """
        Applies optical flow to all consecutive pairs in frames and horizontally concatenates
        the 4 debug views into wide timeline images.
        """
        all_masks = []
        all_hsvs = []
        all_grids = []
        all_clusters = []
        
        for i in range(len(frames) - 1):
            prev_img = frames[i]
            curr_img = frames[i+1]
            flow = self.calculate_optical_flow([prev_img, curr_img])
            
            # 1. Rain Mask
            curr_gray = self.extract_rain_mask(curr_img)
            curr_gray_bgr = cv2.cvtColor(curr_gray, cv2.COLOR_GRAY2BGR)
            
            # 2. HSV Heatmap
            hsv = np.zeros((flow.shape[0], flow.shape[1], 3), dtype=np.uint8)
            hsv[..., 1] = 255
            mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            hsv[..., 0] = ang * 180 / np.pi / 2
            hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
            bgr_flow = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            
            # 3. Flow Vector Grid
            grid_img = curr_img.copy()
            step = 16
            h, w = curr_img.shape[:2]
            y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
            fx, fy = flow[y,x].T
            lines = np.vstack([x, y, x+fx*3, y+fy*3]).T.reshape(-1, 2, 2)
            lines = np.int32(lines + 0.5)
            cv2.polylines(grid_img, lines, 0, (0, 255, 0), 1)
            for (x1, y1), (_x2, _y2) in lines:
                cv2.circle(grid_img, (x1, y1), 1, (0, 255, 0), -1)
            grid_img_bgr = cv2.cvtColor(grid_img, cv2.COLOR_RGB2BGR)
            
            # 4. Clusters
            clusters = self.get_all_rain_clusters(
                curr_img, flow, user_px, user_py, 
                scan_radius=800, min_dbz=min_dbz, cluster_dist=25
            )
            cluster_img = curr_img.copy()
            for c in clusters:
                cx, cy = c["cx"], c["cy"]
                vx, vy = c["vx"], c["vy"]
                size = c.get("size", 10)
                r = int(math.sqrt(size) * 1.5)
                cv2.rectangle(cluster_img, (cx - r, cy - r), (cx + r, cy + r), (255, 0, 255), 1)
                cv2.arrowedLine(cluster_img, (cx, cy), (int(cx + vx*3), int(cy + vy*3)), (255, 255, 0), 2, tipLength=0.3)
            cluster_img_bgr = cv2.cvtColor(cluster_img, cv2.COLOR_RGB2BGR)
            
            # Draw frame index text
            cv2.putText(curr_gray_bgr, f"Flow {i+1}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
            cv2.putText(bgr_flow, f"Flow {i+1}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
            cv2.putText(grid_img_bgr, f"Flow {i+1}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
            cv2.putText(cluster_img_bgr, f"Flow {i+1}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)
            
            # Draw vertical divider
            cv2.line(curr_gray_bgr, (w-2, 0), (w-2, h-1), (80, 80, 80), 3)
            cv2.line(bgr_flow, (w-2, 0), (w-2, h-1), (80, 80, 80), 3)
            cv2.line(grid_img_bgr, (w-2, 0), (w-2, h-1), (80, 80, 80), 3)
            cv2.line(cluster_img_bgr, (w-2, 0), (w-2, h-1), (80, 80, 80), 3)
            
            all_masks.append(curr_gray_bgr)
            all_hsvs.append(bgr_flow)
            all_grids.append(grid_img_bgr)
            all_clusters.append(cluster_img_bgr)
            
        final_mask = np.hstack(all_masks)
        final_hsv = np.hstack(all_hsvs)
        final_grid = np.hstack(all_grids)
        final_cluster = np.hstack(all_clusters)
        
        # Scale to 50% so it's not too huge (2000x400)
        final_mask = cv2.resize(final_mask, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        final_hsv = cv2.resize(final_hsv, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        final_grid = cv2.resize(final_grid, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        final_cluster = cv2.resize(final_cluster, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        
        images = {}
        _, buf = cv2.imencode(".png", final_mask)
        images["rain_mask"] = buf.tobytes()
        _, buf = cv2.imencode(".png", final_hsv)
        images["flow_hsv"] = buf.tobytes()
        _, buf = cv2.imencode(".png", final_grid)
        images["flow_grid"] = buf.tobytes()
        _, buf = cv2.imencode(".png", final_cluster)
        images["clusters"] = buf.tobytes()
        
        return images
        
    def get_flow_vector_at(self, flow: np.ndarray, x: int, y: int) -> Tuple[float, float]:
        """Returns the (dx, dy) velocity vector from optical flow array at given pixel."""
        if x < 0 or x >= flow.shape[1] or y < 0 or y >= flow.shape[0]:
            return 0.0, 0.0
            
        vx = float(flow[y, x, 0])
        vy = float(flow[y, x, 1])
        return vx, vy

    def extrapolate_rain_at_pixel(self, img: np.ndarray, flow: np.ndarray, px: int, py: int, steps: int, rate: float = 0.0, radius: int = 5) -> float:
        """
        Uses Semi-Lagrangian backward tracking to find the dBZ value that will arrive at (px, py) in 'steps' time intervals.
        Each step corresponds to the time difference between the frames used to compute the optical flow (e.g. 15 mins).
        Positive steps mean predicting into the future.
        If 'rate' is provided, it applies an exponential growth/decay factor per step.
        'radius' is used to search a local neighborhood (e.g. +/- 5 pixels) to account for slight movement inaccuracies and cloud edges.
        """
        if steps == 0:
            return self.get_dbz_at_pixel(img, px, py)
            
        # Get the flow vector at the target pixel
        vx, vy = self.get_flow_vector_at(flow, px, py)
        
        # Calculate source pixel (backward tracking)
        # Assuming linear constant velocity over the steps
        src_x = int(round(px - (vx * steps)))
        src_y = int(round(py - (vy * steps)))
        
        max_dbz = 0.0
        # Check a bounding box of +/- radius around the source pixel
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = src_x + dx
                sy = src_y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = self.get_dbz_at_pixel(img, sx, sy)
                    if d > max_dbz:
                        max_dbz = d
                        
        dbz = max_dbz
        
        if rate != 0.0 and dbz > 0:
            factor = 1.0 + rate
            if factor <= 0:
                dbz = 0.0
            else:
                dbz = float(dbz * (factor ** steps))
                
            if dbz > 75.0:
                dbz = 75.0
            elif dbz < 10.0:
                dbz = 0.0
        
        return float(dbz)

    @staticmethod
    def draw_pin_on_frame(img: np.ndarray, x: int, y: int) -> None:
        """Draws the blue location pin on the image at the specified pixel coordinates."""
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return
        # White halo for contrast
        cv2.circle(img, (x, y), radius=14, color=(255, 255, 255), thickness=5)
        cv2.circle(img, (x, y), radius=20, color=(255, 255, 255), thickness=3)
        # Blue target body. The frame data is RGB, so this must be RGB blue.
        color = (0, 0, 255)
        cv2.circle(img, (x, y), radius=12, color=color, thickness=4)
        cv2.drawMarker(img, (x, y), color=color, markerType=cv2.MARKER_CROSS, markerSize=24, thickness=4)

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
            predicted_dbz = max(0.0, min(75.0, dbz_now * ((1 + growth_rate) ** eta_steps)))

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

        clusters.sort(key=lambda c: c["eta_min"])
        return clusters

    @staticmethod
    def render_rain_summary(clouds: list, confidence_cutoff_min: int = 90, time_offset_min: float = 0.0, confidence_score: float = 1.0) -> str:
        """
        Generates a smart, non-redundant rain summary line for Telegram.

        - If no reliable clouds: returns a 'no rain' message.
        - If first cloud = strongest: merges into one line.
        - If a stronger cloud follows: shows two distinct lines.
        """
        warning = "\n⚠️ ข้อมูลขาดช่วง (ความแม่นยำต่ำ)" if confidence_score < 1.0 else ""
        
        def fmt_eta(minutes: float) -> str:
            m = int(round(minutes - time_offset_min))
            if m < 0:
                m = 0
            if m < 60:
                return f"~{m}m"
            h = m // 60
            r = m % 60
            return f"~{h}h{r}m" if r else f"~{h}hr"

        def dbz_label(dbz: float) -> str:
            if dbz >= 55: return "ฝนหนักมาก"
            if dbz >= 40: return "ฝนหนัก"
            if dbz >= 25: return "ฝนปานกลาง"
            return "ฝนเบา"

        # Filter for incoming or currently active rain only (-10 to confidence cutoff)
        reliable = [c for c in clouds if c["predicted_dbz"] >= 15 and -10 <= c["eta_min"] <= confidence_cutoff_min]

        if not reliable:
            return f"ℹ️ ไม่พบฝนในระยะ 90 นาทีข้างหน้า{warning}"

        first    = reliable[0]
        strongest = max(reliable, key=lambda c: c["predicted_dbz"])

        if first is strongest:
            lbl = dbz_label(first["predicted_dbz"])
            return f"⚡ ฝนกำลังจะมาใน {fmt_eta(first['eta_min'])} ({int(first['predicted_dbz'])} dBZ — {lbl}){warning}"
        else:
            lbl_f = dbz_label(first["predicted_dbz"])
            lbl_s = dbz_label(strongest["predicted_dbz"])
            return (
                f"⏱ ฝนก้อนแรกใน {fmt_eta(first['eta_min'])} ({int(first['predicted_dbz'])} dBZ — {lbl_f})\n"
                f"⚡ ก้อนหนักกว่ามาทีหลัง {fmt_eta(strongest['eta_min'])} ({int(strongest['predicted_dbz'])} dBZ — {lbl_s}){warning}"
            )

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
        h, w = frame.shape[:2]
        candidates = []
        for dy in range(-scan_radius, scan_radius + 1, 2):
            for dx in range(-scan_radius, scan_radius + 1, 2):
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

            clusters.append({
                "cx": cx, "cy": cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "predicted_dbz": dbz_now,
                "dist": dist,
                "eta_min": eta_min,
                "approaching": approaching,
                "size": len(group),
            })

        clusters.sort(key=lambda c: c["dist"])
        return clusters

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

    @staticmethod
    def generate_radar_tracking_image(
        frame: np.ndarray,
        user_x: int,
        user_y: int,
        clouds: list,
        time_utc: datetime = None,
        all_rain_clusters: list = None,
    ) -> Optional[bytes]:
        """Generate zoomed radar tracking image.
        
        Always renders if there are any rain clusters in the area (approaching or not).
        - clouds: approaching-only clusters (ETA-filtered)
        - all_rain_clusters: every rain cluster visible in scan radius
        """
        # Determine what to draw
        display_clouds = clouds or []          # approaching, drawn with direction label
        ambient_clouds = [                     # non-approaching, drawn as plain circles
            c for c in (all_rain_clusters or [])
            if not any(
                math.hypot(c["cx"] - d["cx"], c["cy"] - d["cy"]) < 30
                for d in display_clouds
            )
        ] if all_rain_clusters else []

        if frame is None or (not display_clouds and not ambient_clouds):
            return None
        
        # Crop a 240x240 region around the user
        crop_r = 120
        h, w = frame.shape[:2]
        
        x1 = max(0, user_x - crop_r)
        y1 = max(0, user_y - crop_r)
        x2 = min(w, user_x + crop_r)
        y2 = min(h, user_y + crop_r)
        
        crop_img = frame[y1:y2, x1:x2].copy()
        
        # Scale up by 3x for sharp, zoomed-in image in Telegram
        scale = 3.0
        img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        
        ux = int((user_x - x1) * scale)
        uy = int((user_y - y1) * scale)
        
        # Draw user pin in blue to match the main location target
        cv2.circle(img, (ux, uy), radius=int(6 * scale), color=(255, 255, 255), thickness=int(3 * scale))
        cv2.drawMarker(img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(10 * scale), int(3 * scale))
        
        def _dbz_color(dbz):
            if dbz >= 60: return (155, 89, 182)   # Purple
            elif dbz >= 50: return (231, 76, 60)  # Red
            elif dbz >= 40: return (243, 156, 18) # Orange
            elif dbz >= 30: return (241, 196, 15) # Yellow
            else: return (46, 204, 113)            # Green

        def _draw_cloud(c_orig, is_approaching):
            cx_orig, cy_orig = c_orig["cx"], c_orig["cy"]
            # Skip if outside crop (with generous margin)
            if cx_orig < x1 - 80 or cx_orig > x2 + 80 or cy_orig < y1 - 80 or cy_orig > y2 + 80:
                return
            cx = int((cx_orig - x1) * scale)
            cy = int((cy_orig - y1) * scale)
            dbz = c_orig.get("predicted_dbz", c_orig.get("dbz_now", 20))
            vx = c_orig.get("vx", 0)
            vy = c_orig.get("vy", 0)

            if is_approaching:
                # Approaching: solid colour circle + yellow arrow + ETA label
                color = _dbz_color(dbz)
                cv2.circle(img, (cx, cy), int(12 * scale), color, int(1.5 * scale))
                # Arrow toward destination
                vx_scaled = int(vx * scale * 3.0)
                vy_scaled = int(vy * scale * 3.0)
                if vx_scaled == 0 and vy_scaled == 0:
                    cv2.arrowedLine(img, (cx, cy), (ux, uy), (255, 255, 0), int(1.5 * scale), tipLength=0.15)
                else:
                    cv2.arrowedLine(img, (cx, cy), (cx + vx_scaled, cy + vy_scaled), (255, 255, 0), int(1.5 * scale), tipLength=0.3)
                # ETA label
                eta = c_orig.get("eta_min", 0)
                sign = "-" if eta < 0 else "~"
                abs_eta = int(abs(eta))
                time_str = f"{abs_eta}m" if abs_eta < 60 else f"{abs_eta//60}h{abs_eta%60}m"
                cv2.putText(img, f"{sign}{time_str}", (cx + int(14 * scale), cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45 * scale, (255, 255, 255), int(1.5 * scale))
            else:
                # Ambient (not approaching): dashed/thin circle + white/grey arrow
                color = _dbz_color(dbz)
                # Draw as dashed circle approximation using arc segments
                for angle_deg in range(0, 360, 30):
                    import math as _m
                    a1 = _m.radians(angle_deg)
                    a2 = _m.radians(angle_deg + 20)
                    r = int(10 * scale)
                    p1 = (int(cx + r * _m.cos(a1)), int(cy + r * _m.sin(a1)))
                    p2 = (int(cx + r * _m.cos(a2)), int(cy + r * _m.sin(a2)))
                    cv2.line(img, p1, p2, color, int(scale * 0.8))
                # Wind direction arrow (white, shorter)
                vx_scaled = int(vx * scale * 2.5)
                vy_scaled = int(vy * scale * 2.5)
                v_mag = math.hypot(vx_scaled, vy_scaled)
                if v_mag > 2:
                    cv2.arrowedLine(img, (cx, cy), (cx + vx_scaled, cy + vy_scaled),
                                    (200, 200, 200), max(1, int(scale * 0.8)), tipLength=0.3)
                # dBZ label in muted colour
                cv2.putText(img, f"{int(dbz)}", (cx + int(11 * scale), cy - int(5 * scale)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35 * scale, (200, 200, 200), int(scale * 0.7))

        # Filter for incoming clouds only (ETA >= -5) and limit to top 3 strongest
        incoming = [c for c in display_clouds if c.get("eta_min", 9999) >= -5]
        incoming.sort(key=lambda c: c.get("predicted_dbz", 0), reverse=True)
        for c in incoming[:3]:
            _draw_cloud(c, is_approaching=True)

        # Draw ambient (non-approaching) clusters, up to 8
        ambient_clouds.sort(key=lambda c: c.get("dist", 9999))
        for c in ambient_clouds[:8]:
            _draw_cloud(c, is_approaching=False)

        # Add IDC timestamp overlay
        if time_utc:
            try:
                from PIL import Image, ImageFont, ImageDraw
                img_pil = Image.fromarray(img).convert("RGBA")
                time_str_idc = time_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
                try:
                    fnt = _load_thai_font(int(14 * scale))
                except:
                    fnt = _load_thai_font(int(14 * scale))

                draw = ImageDraw.Draw(img_pil, "RGBA")

                # Handling older Pillow versions where textbbox might not be available
                if hasattr(draw, 'textbbox'):
                    left, top, right, bottom = draw.textbbox((0, 0), time_str_idc, font=fnt)
                    text_w, text_h = right - left, bottom - top
                else:
                    text_w, text_h = draw.textsize(time_str_idc, font=fnt)

                pad = int(4 * scale)
                x_pos = img_pil.width - text_w - int(8 * scale)
                y_pos = int(8 * scale)

                draw.rectangle([x_pos-pad, y_pos-pad, x_pos+text_w+pad, y_pos+text_h+pad], fill=(0, 0, 0, 200))
                draw.text((x_pos, y_pos), time_str_idc, fill=(255, 255, 255, 255), font=fnt)

                img = np.array(img_pil.convert("RGB"))
            except Exception as e:
                print("PIL ERROR:", e)

        # Convert RGB back to BGR for cv2.imencode
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        is_success, buffer = cv2.imencode(".png", img_bgr)
        return buffer.tobytes() if is_success else None

    @staticmethod
    def generate_timeline_image(clouds: list) -> Optional[bytes]:
        if not clouds:
            return None
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None
            
        width, height = 800, 430
        img = Image.new("RGBA", (width, height), (30, 30, 30, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        
        font       = _load_thai_font(16)
        font_small = _load_thai_font(14)
            
        baseline_y = 350
        draw.line([(0, baseline_y), (width, baseline_y)], fill=(100, 100, 100, 255), width=2)
        
        def time_to_x(t):
            return int(50 + (t - (-60)) * (700 / 210.0))
            
        x_90 = time_to_x(90)
        draw.line([(x_90, 50), (x_90, height - 20)], fill=(74, 144, 226, 128), width=2)
        draw.text((x_90 + 5, 60), "Confidence\nBoundary", fill=(74, 144, 226, 200), font=font_small)
        
        base_x = time_to_x(0)
        draw.line([(base_x, 40), (base_x, height - 20)], fill=(255, 255, 255, 200), width=2)
        draw.text((base_x - 15, 25), "NOW", font=font, fill=(255, 255, 255, 255))

        # Bin clouds by X coordinate to prevent overlapping exact same ETA
        # Also keep growth_rate for the dominant cloud at each bin
        binned_clouds = {}
        for c in clouds:
            eta = c["eta_min"]
            dbz = c["predicted_dbz"]
            growth = c.get("growth_rate", 0.0)
            x = time_to_x(eta)
            x = max(20, min(780, x))
            if x not in binned_clouds or dbz > binned_clouds[x]["dbz"]:
                binned_clouds[x] = {"eta": eta, "dbz": dbz, "growth": growth}

        last_x = -999
        y_offsets = {}

        for x in sorted(binned_clouds.keys()):
            eta    = binned_clouds[x]["eta"]
            dbz    = binned_clouds[x]["dbz"]
            growth = binned_clouds[x]["growth"]  # rate per 15min (e.g. 0.3 = +30%)

            h = int(dbz * 4)

            if dbz >= 60: color = (155, 89, 182, 230)   # Purple
            elif dbz >= 50: color = (231, 76, 60, 230)  # Red
            elif dbz >= 40: color = (243, 156, 18, 230) # Orange
            elif dbz >= 30: color = (241, 196, 15, 230) # Yellow
            else: color = (46, 204, 113, 230)            # Green

            if eta > 90:
                color = (color[0], color[1], color[2], 100)

            draw.rectangle([(x-10, baseline_y-h), (x+10, baseline_y)], fill=color)
            draw.text((x-12, baseline_y-h-20), f"{int(dbz)}", fill=(255, 255, 255, 255), font=font)

            # ── Growth / decay trend arrow ─────────────────────────────────
            arrow_y_base = baseline_y - h - 22
            growth_pct = growth * 100.0
            if growth_pct > 5.0:
                # Growing: green upward triangle above bar
                arr_color = (46, 213, 115, 230)   # Bright green
                pts = [(x, arrow_y_base - 14), (x - 7, arrow_y_base), (x + 7, arrow_y_base)]
                draw.polygon(pts, fill=arr_color)
                draw.text((x - 18, arrow_y_base - 30), f"+{growth_pct:.0f}%", fill=arr_color, font=font_small)
            elif growth_pct < -5.0:
                # Decaying: red downward triangle above bar
                arr_color = (255, 71, 87, 230)    # Bright red
                pts = [(x, arrow_y_base), (x - 7, arrow_y_base - 14), (x + 7, arrow_y_base - 14)]
                draw.polygon(pts, fill=arr_color)
                draw.text((x - 20, arrow_y_base - 30), f"{growth_pct:.0f}%", fill=arr_color, font=font_small)
            else:
                # Stable: small grey dash
                draw.rectangle([(x - 6, arrow_y_base - 10), (x + 6, arrow_y_base - 7)],
                                fill=(160, 160, 160, 180))

            # Smart text offset to avoid overlapping ETA labels
            y_off = 20
            if x - last_x < 40:
                prev_off = y_offsets.get(last_x, 50)
                y_off = 35 if prev_off == 20 else (50 if prev_off == 35 else 20)
            y_offsets[x] = y_off
            last_x = x

            m = int(round(abs(eta)))
            t_str = f"~{m}m" if m < 60 else f"~{m//60}h{m%60}m"
            sign = "-" if eta < 0 else ""
            draw.text((x-15, baseline_y+y_off), f"{sign}{t_str}", fill=(200, 200, 200, 255), font=font_small)

        # ── Legend ─────────────────────────────────────────────────────────
        leg_y = height - 20
        # Growing: draw upward triangle + label
        draw.polygon([(18, leg_y + 2), (12, leg_y + 12), (24, leg_y + 12)], fill=(46, 213, 115, 200))
        draw.text((28, leg_y), "กำลังแรงขึ้น", fill=(46, 213, 115, 200), font=font_small)
        # Decaying: draw downward triangle + label (wide at top → narrow at bottom)
        draw.polygon([(162, leg_y + 2), (174, leg_y + 2), (168, leg_y + 12)], fill=(255, 71, 87, 200))
        draw.text((178, leg_y), "อ่อนกำลังลง", fill=(255, 71, 87, 200), font=font_small)
        # Stable: draw dash + label
        draw.rectangle([(313, leg_y + 5), (327, leg_y + 8)], fill=(160, 160, 160, 200))
        draw.text((332, leg_y), "คงที่", fill=(160, 160, 160, 200), font=font_small)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


    @staticmethod
    def generate_multiframe_analysis_image(
        frames: "List[np.ndarray]",
        flow: "np.ndarray",
        user_x: int,
        user_y: int,
        clouds: list,
        processor: "TMDRadarProcessor",
        time_utc: "Optional[datetime]" = None,
        gap_minutes: float = 15.0,
        frame_timestamps: "Optional[List[int]]" = None,
    ) -> "Optional[bytes]":
        """
        Produces a horizontal strip of radar frame thumbnails with cloud-cluster
        trajectory overlays and per-frame growth/decay measurements.

        Layout (one column per frame, oldest → newest left to right):

            ┌──────────┬──────────┬──────────┬──────────┐
            │ t-45m    │ t-30m    │ t-15m    │ NOW      │  ← timestamp row
            │[radar]   │[radar]   │[radar]   │[radar]   │  ← cropped thumbnail
            │ ●──→     │  ●──→   │   ●──→  │    ●     │  ← cluster dot+arrow
            │ 32 dBZ   │ 38 dBZ  │ 42 dBZ  │ 45 dBZ  │  ← dBZ per frame
            │  +14%    │  +19%   │  +11%   │    --   │  ← growth/decay Δ
            └──────────┴──────────┴──────────┴──────────┘

        Parameters
        ----------
        frames      : RGB numpy frames (oldest first), at most 6 are used.
        flow        : Dense optical flow computed from the last 2 frames.
        user_x/y    : Pixel coordinate of the user's location in each frame.
        clouds      : Cloud cluster list from find_approaching_clouds().
        processor   : TMDRadarProcessor instance (for dbz/wind helpers).
        time_utc    : Timestamp of the LATEST frame (for labelling).
        gap_minutes : Average minutes between consecutive frames (default 15).
        frame_timestamps: List of UTC epoch ints, one per frame (oldest first).
                      When provided, each panel label uses the exact scan time
                      instead of time_utc - steps×gap_minutes estimate.
        """
        try:
            from PIL import Image as PILImage, ImageDraw as PILDraw, ImageFont as PILFont
        except ImportError:
            return None

        if not frames or len(frames) < 2:
            return None

        # ── Layout constants ────────────────────────────────────────────────
        MAX_FRAMES = 6
        use_frames = frames[-MAX_FRAMES:]          # up to 6, oldest first
        n = len(use_frames)

        THUMB_W, THUMB_H = 200, 200                # thumbnail size (px)
        TITLE_H  = 20                              # top title bar
        HEADER_H = 28                              # timestamp row height (below title)
        DBZ_ROW_H = 22                             # dBZ label row
        GROWTH_ROW_H = 20                          # growth/decay row
        PANEL_H = THUMB_H + TITLE_H + HEADER_H + DBZ_ROW_H + GROWTH_ROW_H
        TOTAL_W = THUMB_W * n
        TOTAL_H = PANEL_H

        BG_COLOR   = (18, 18, 30, 255)            # near-black bg
        GRID_COLOR = (50, 50, 70, 255)
        TEXT_WHITE = (230, 230, 230, 255)
        TEXT_DIM   = (140, 140, 160, 255)
        NOW_BORDER = (74, 144, 226, 255)           # blue highlight for NOW panel

        canvas = PILImage.new("RGBA", (TOTAL_W, TOTAL_H), BG_COLOR)
        draw   = PILDraw.Draw(canvas, "RGBA")

        # ── Font loading ─────────────────────────────────────────────────────
        font_sm  = _load_thai_font(11)
        font_med = _load_thai_font(13)

        # ── Title bar (full-width, above all panels) ─────────────────────────
        draw.rectangle([0, 0, TOTAL_W - 1, TITLE_H - 1], fill=(28, 28, 50, 255))
        title = f"Radar Analysis  ({n} frames × {int(gap_minutes)}m)"
        draw.text((8, 3), title, font=font_sm, fill=(180, 180, 220, 220))


        # ── Helper: dBZ → colour (RGB) ───────────────────────────────────────
        def _dbz_color(dbz: float):
            if dbz >= 60: return (155, 89, 182)   # Purple
            if dbz >= 50: return (231, 76,  60)   # Red
            if dbz >= 40: return (243, 156, 18)   # Orange
            if dbz >= 30: return (241, 196, 15)   # Yellow
            if dbz >= 15: return (46,  204, 113)  # Green
            return (100, 100, 100)                # Gray (trace)

        # ── Identify top clouds to trace (max 2 strongest) ──────────────────
        incoming = sorted(
            [c for c in clouds if c.get("eta_min", 0) >= -30],
            key=lambda c: c.get("predicted_dbz", 0),
            reverse=True,
        )[:2]

        # ── Per-frame cluster positions & dBZ ───────────────────────────────
        # For cloud c in the CURRENT frame (index = n-1),
        # its position in frame[i] is back-traced by (n-1-i) steps.
        # cluster_data[cloud_idx][frame_idx] = {"px": int, "py": int, "dbz": float}
        cluster_data: list = []
        for c in incoming:
            vx, vy = c.get("vx", 0.0), c.get("vy", 0.0)
            cx_now, cy_now = int(c["cx"]), int(c["cy"])
            pts = []
            for fi in range(n):
                steps_back = (n - 1 - fi)          # 0 for latest frame
                px = int(round(cx_now - vx * steps_back))
                py = int(round(cy_now - vy * steps_back))
                dbz = processor._get_max_dbz_in_radius(use_frames[fi], px, py, radius=12)
                pts.append({"px": px, "py": py, "dbz": dbz})
            cluster_data.append(pts)

        # ── Build each panel ─────────────────────────────────────────────────
        crop_r = THUMB_W // 2

        for fi in range(n):
            frame = use_frames[fi]
            is_now = (fi == n - 1)
            panel_x = fi * THUMB_W

            # Frame timestamp label — prefer per-frame OCR timestamp over estimate
            # frame_timestamps is aligned to ALL frames; use_frames is the last MAX_FRAMES
            ts_offset = len(frames) - n  # oldest used frame index in original list
            frame_ts_idx = ts_offset + fi  # index in original frame_timestamps list

            if (frame_timestamps and
                    frame_ts_idx < len(frame_timestamps) and
                    frame_timestamps[frame_ts_idx]):
                frame_dt = datetime.fromtimestamp(
                    frame_timestamps[frame_ts_idx], tz=ZoneInfo("Asia/Bangkok")
                )
                hm = frame_dt.strftime("%H:%M")
                ts_label = f"NOW  {hm}" if is_now else hm
            elif time_utc is not None:
                delta_back = (n - 1 - fi) * gap_minutes
                frame_dt = time_utc - timedelta(minutes=delta_back)
                hm = frame_dt.astimezone(ZoneInfo("Asia/Bangkok")).strftime("%H:%M")
                ts_label = f"NOW  {hm}" if is_now else f"-{int(delta_back)}m  {hm}"
            else:
                ts_label = "NOW" if is_now else f"-{(n-1-fi)*int(gap_minutes)}m"

            # Header background  (sits below TITLE_H)
            hdr_color = (30, 60, 100, 255) if is_now else (28, 28, 45, 255)
            draw.rectangle([panel_x, TITLE_H, panel_x + THUMB_W - 1, TITLE_H + HEADER_H - 1],
                           fill=hdr_color)
            draw.text((panel_x + 6, TITLE_H + 6), ts_label, font=font_med,
                      fill=(255, 255, 255, 255) if is_now else TEXT_DIM)

            # "NOW" border highlight
            if is_now:
                draw.rectangle(
                    [panel_x, TITLE_H, panel_x + THUMB_W - 1, PANEL_H - 1],
                    outline=NOW_BORDER, width=2,
                )

            # ── Crop thumbnail from frame ─────────────────────────────────
            fh, fw = frame.shape[:2]
            x1 = max(0, user_x - crop_r)
            y1 = max(0, user_y - crop_r)
            x2 = min(fw, user_x + crop_r)
            y2 = min(fh, user_y + crop_r)
            crop = frame[y1:y2, x1:x2].copy()

            if crop.shape[0] == 0 or crop.shape[1] == 0:
                continue

            thumb_top = TITLE_H + HEADER_H

            # Resize to fixed THUMB_W × THUMB_H
            crop_resized = cv2.resize(crop, (THUMB_W, THUMB_H), interpolation=cv2.INTER_LANCZOS4)
            thumb_pil = PILImage.fromarray(crop_resized, mode="RGB").convert("RGBA")
            thumb_draw = PILDraw.Draw(thumb_pil, "RGBA")

            # Scale factors for mapping original coords into thumbnail
            sx = THUMB_W / max(1, x2 - x1)
            sy = THUMB_H / max(1, y2 - y1)
            # User pin position in thumbnail
            ux_t = int((user_x - x1) * sx)
            uy_t = int((user_y - y1) * sy)
            # Clamp
            ux_t = max(4, min(THUMB_W - 4, ux_t))
            uy_t = max(4, min(THUMB_H - 4, uy_t))

            # Draw user pin (white ring + blue cross)
            thumb_draw.ellipse([ux_t - 6, uy_t - 6, ux_t + 6, uy_t + 6],
                               outline=(255, 255, 255, 220), width=2)
            thumb_draw.line([(ux_t - 5, uy_t), (ux_t + 5, uy_t)], fill=(0, 120, 255, 255), width=2)
            thumb_draw.line([(ux_t, uy_t - 5), (ux_t, uy_t + 5)], fill=(0, 120, 255, 255), width=2)

            # ── Draw each tracked cluster in this frame ───────────────────
            for ci, pts in enumerate(cluster_data):
                pt = pts[fi]
                dbz = pt["dbz"]
                if dbz == 0 and not any(pts[j]["dbz"] > 0 for j in range(fi + 1, n)):
                    continue  # Nothing to show

                # Cluster pixel in thumbnail coords
                cpx = int((pt["px"] - x1) * sx)
                cpy = int((pt["py"] - y1) * sy)
                cpx = max(4, min(THUMB_W - 4, cpx))
                cpy = max(4, min(THUMB_H - 4, cpy))

                c_rgb = _dbz_color(dbz) if dbz > 0 else (80, 80, 80)
                c_rgba = c_rgb + (200,)

                # Cluster circle
                r = 8
                thumb_draw.ellipse([cpx - r, cpy - r, cpx + r, cpy + r],
                                   outline=c_rgba, width=2)

                # Arrow pointing toward user (or next position)
                vx_ci = incoming[ci].get("vx", 0.0)
                vy_ci = incoming[ci].get("vy", 0.0)
                arrow_len = 18
                mag = math.sqrt(vx_ci**2 + vy_ci**2) or 1
                ax = int(cpx + (vx_ci / mag) * arrow_len)
                ay = int(cpy + (vy_ci / mag) * arrow_len)
                if abs(ax - cpx) > 2 or abs(ay - cpy) > 2:
                    thumb_draw.line([(cpx, cpy), (ax, ay)],
                                    fill=(255, 255, 0, 200), width=2)
                    # Arrowhead (simple triangle)
                    dx, dy = ax - cpx, ay - cpy
                    perp_x, perp_y = -dy, dx
                    pmag = math.sqrt(perp_x**2 + perp_y**2) or 1
                    tip1 = (ax - int((dx - perp_x / pmag * 4) * 0.4),
                            ay - int((dy - perp_y / pmag * 4) * 0.4))
                    tip2 = (ax - int((dx + perp_x / pmag * 4) * 0.4),
                            ay - int((dy + perp_y / pmag * 4) * 0.4))
                    thumb_draw.polygon([ax, ay, tip1[0], tip1[1], tip2[0], tip2[1]],
                                       fill=(255, 255, 0, 200))

                # Trajectory line connecting cluster across frames
                if fi > 0:
                    prev_pt = pts[fi - 1]
                    ppx = int((prev_pt["px"] - x1) * sx)
                    ppy = int((prev_pt["py"] - y1) * sy)
                    ppx = max(0, min(THUMB_W - 1, ppx))
                    ppy = max(0, min(THUMB_H - 1, ppy))
                    thumb_draw.line([(ppx, ppy), (cpx, cpy)],
                                    fill=(255, 200, 0, 80), width=1)

            # Paste thumbnail onto canvas
            canvas.paste(thumb_pil, (panel_x, thumb_top))

            # ── dBZ row ───────────────────────────────────────────────────
            dbz_y = thumb_top + THUMB_H
            draw.rectangle([panel_x, dbz_y, panel_x + THUMB_W - 1, dbz_y + DBZ_ROW_H - 1],
                           fill=(22, 22, 38, 255))

            # Report max dBZ across tracked clusters in this frame
            max_dbz_frame = max(
                (pts[fi]["dbz"] for pts in cluster_data), default=0.0
            )
            # For mock scenario: if no real radar dBZ, use cloud's dbz_now
            if max_dbz_frame == 0 and incoming:
                c0 = incoming[0]
                steps_back = (n - 1 - fi)
                gr = c0.get("growth_rate", 0.0)
                max_dbz_frame = max(0.0, min(75.0, c0.get("dbz_now", 0.0) * ((1 + gr) ** (-steps_back))))

            if max_dbz_frame > 0:
                dbz_col = _dbz_color(max_dbz_frame) + (230,)
                dbz_lbl = f"{int(max_dbz_frame)} dBZ"
            else:
                dbz_col = TEXT_DIM
                dbz_lbl = "-- dBZ"
            draw.text((panel_x + 6, dbz_y + 4), dbz_lbl, font=font_sm, fill=dbz_col)

            # ── Growth/decay row ──────────────────────────────────────────
            gd_y = dbz_y + DBZ_ROW_H
            draw.rectangle([panel_x, gd_y, panel_x + THUMB_W - 1, gd_y + GROWTH_ROW_H - 1],
                           fill=(16, 16, 30, 255))

            if fi == 0:
                gd_lbl = "  --"
                gd_col = TEXT_DIM
            elif max_dbz_frame == 0:
                gd_lbl = "  --"
                gd_col = TEXT_DIM
            else:
                prev_max = max(
                    (pts[fi - 1]["dbz"] for pts in cluster_data), default=0.0
                )
                # Fallback for mock (no real radar dBZ in past frame)
                if prev_max == 0 and incoming:
                    c0 = incoming[0]
                    gr = c0.get("growth_rate", 0.0)
                    prev_max = max(0.0, min(75.0, c0.get("dbz_now", 0.0) * ((1 + gr) ** (-(n - fi)))))
                if prev_max == 0:
                    gd_lbl = " new"
                    gd_col = (46, 204, 113, 230)
                else:
                    delta_pct = ((max_dbz_frame - prev_max) / prev_max) * 100.0
                    sign = "+" if delta_pct >= 0 else ""
                    gd_lbl = f"{sign}{delta_pct:.0f}%"
                    gd_col = (46, 204, 113, 230) if delta_pct >= 0 else (231, 76, 60, 230)

            draw.text((panel_x + 6, gd_y + 3), gd_lbl, font=font_sm, fill=gd_col)

        # ── Draw separators on top ────────────────────────────────────────────
        for fi in range(1, n):
            panel_x = fi * THUMB_W
            draw.line([(panel_x, TITLE_H), (panel_x, PANEL_H)], fill=(80, 80, 100, 220), width=2)

        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    def calculate_lagrangian_growth(self, frames: list, flow: np.ndarray, target_x: int, target_y: int, steps_ahead: int, max_lookback_frames: int = 2) -> float:
        """
        Calculates the true growth of the specific air mass that will hit target_x, target_y in `steps_ahead` frames.
        It tracks the air mass backwards in time to compare its current intensity with its past intensity.
        `max_lookback_frames` determines how far back to trace (e.g. 2 = 30 mins).
        """
        if len(frames) < 2:
            return 0.0
            
        vx, vy = self.get_flow_vector_at(flow, target_x, target_y)
        
        # Where is the cloud that will hit the target located CURRENTLY?
        curr_src_x = int(round(target_x - vx * steps_ahead))
        curr_src_y = int(round(target_y - vy * steps_ahead))
        
        # Search in a 30-pixel radius (~30km) to lock onto the MACRO storm cell
        # rather than tracking a micro air parcel which may disperse or shift.
        curr_dbz = self._get_max_dbz_in_radius(frames[-1], curr_src_x, curr_src_y, radius=30)
        
        past_dbz = 0.0
        
        # Look backwards through frames to find the oldest valid dBZ
        max_lookback = min(max_lookback_frames, len(frames) - 1)
        for i in range(1, max_lookback + 1):
            prev_x = int(round(curr_src_x - i * vx))
            prev_y = int(round(curr_src_y - i * vy))
            # Index offset: i=1 -> frames[-2]
            dbz = self._get_max_dbz_in_radius(frames[-(i + 1)], prev_x, prev_y, radius=30)
            if dbz > 0:
                past_dbz = dbz # Keep overwriting to get the OLDEST available > 0
                
        if curr_dbz == 0 and past_dbz == 0:
            return 0.0
        elif curr_dbz > 0 and past_dbz == 0:
            return 50.0  # Formed
        elif curr_dbz == 0 and past_dbz > 0:
            return -100.0 # Dissipated
            
        growth_pct = ((curr_dbz - past_dbz) / past_dbz) * 100.0
        return max(-100.0, min(100.0, growth_pct))

    @staticmethod
    def parse_html_timestamp(html: str) -> Optional[datetime]:
        """Parse TMD station PHP embed version string, e.g. v=250626_1030 → UTC datetime."""
        match = re.search(r'v=(\d{6})_(\d{4})', html)
        if not match:
            return None
        date_str = match.group(1)
        time_str = match.group(2)
        year = int('20' + date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        bkk_tz = ZoneInfo('Asia/Bangkok')
        dt_bkk = datetime(year, month, day, hour, minute, tzinfo=bkk_tz)
        return dt_bkk.astimezone(timezone.utc)

    async def fetch_station_timestamp_utc(self) -> Optional[datetime]:
        """Fetch the authoritative latest-frame timestamp from the TMD station PHP page."""
        prefix = self.station_code[:3]
        php_url = f"https://weather.tmd.go.th/{prefix}.php"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(php_url)
                if resp.status_code == 200:
                    return self.parse_html_timestamp(resp.text)
        except Exception as e:
            logger.warning(f"[{self.station_code}] HTML timestamp fetch failed: {e}")
        return None

    async def fetch_latest_image_bytes(self) -> Optional[bytes]:
        """Fetches the latest static radar image (Polling method)."""
        
        url = self.config.static_image_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
        except Exception:
            pass
        return None

    async def decode_static_frame(self) -> Optional[np.ndarray]:
        """Download and decode the latest static radar image as an RGB numpy frame."""
        static_bytes = await self.fetch_latest_image_bytes()
        if not static_bytes:
            return None
        arr = np.frombuffer(static_bytes, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    async def fetch_loop_gif_and_extract_frames(self) -> Tuple[List[np.ndarray], Optional['datetime'], Optional[bytes]]:
        """Fetches the Loop.gif and extracts frames, the Last-Modified datetime, and raw GIF bytes."""
        
        loop_bytes = None
        dt = None
                
        if not loop_bytes:
            # Use the verified loop_gif_url from station config.
            # If empty, the station has no loop GIF (e.g. kkn120 → returns 404).
            url = self.config.loop_gif_url
            if not url:
                logger.warning(
                    f"[{self.station_code}] No loop_gif_url configured "
                    f"(station has no loop GIF from TMD). Returning empty frames."
                )
                return [], None, None
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        loop_bytes = response.content
                        last_modified = response.headers.get("last-modified")
                        
                        try:
                            php_url = f"https://weather.tmd.go.th/{self.station_code[:3]}.php"
                            php_resp = await client.get(php_url)
                            if php_resp.status_code == 200:
                                dt = self.parse_html_timestamp(php_resp.text)
                        except Exception as e:
                            print(f"Error fetching exact timestamp from HTML: {e}")
                            
                        if dt is None and last_modified:
                            try:
                                dt = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                            except Exception as e:
                                print(f"Error parsing date: {e}")
                    else:
                        logger.warning(
                            f"[{self.station_code}] Loop GIF URL returned HTTP {response.status_code}: {url}"
                        )
            except Exception as e:
                print(f"Error fetching loop gif: {e}")

                
        if loop_bytes:
            try:
                img = Image.open(io.BytesIO(loop_bytes))
                frames = []
                for frame in ImageSequence.Iterator(img):
                    frames.append(np.array(frame.copy().convert("RGB")))

                if frames:
                    target_h, target_w = frames[0].shape[:2]
                    normalized_frames = []
                    for frame in frames:
                        if frame.shape[:2] != (target_h, target_w):
                            frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
                        normalized_frames.append(frame)
                    frames = normalized_frames
                    
                # Optimize memory: keep only the last 12 frames (approx 3 hours of radar data)
                # to prevent OOM spikes during downstream high-res GIF generation.
                if len(frames) > 12:
                    frames = frames[-12:]
                    
                try:
                    ocr_svc = OCRService()
                    if len(frames) > 0:
                        fallback_ts = int(dt.timestamp()) if dt else int(time.time())
                        ts = await ocr_svc.get_frame_timestamp(frames[-1], fallback_ts=fallback_ts)
                        if ts is not None:
                            dt = datetime.fromtimestamp(ts, timezone.utc)
                except Exception as e:
                    print(f"Error in OCR: {e}")

                return frames, dt, loop_bytes
            except Exception as e:
                print(f"Error processing loop gif: {e}")
        return [], None, None

    async def fetch_loop_history_bytes(self) -> List[bytes]:
        """
        Fetches the history of images from the loop page.
        This is a stub. Real implementation requires scraping the loop.php HTML.
        For MVP, we just try to fetch the latest static image as history.
        """
        # TODO: Implement actual HTML scraping of self.config.loop_page_url
        # For now, return an empty list to fallback to polling
        return []

    async def save_polled_frame(self, image_bytes: bytes) -> str:
        """Saves a polled image byte sequence to Google Cloud Storage with a timestamp."""
        
        timestamp = int(time.time())
        filename = f"radar/{self.station_code}/{self.station_code}_{timestamp}.gif"
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
        
        # Use sync GCS upload with asyncio.to_thread
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        import asyncio
        await asyncio.to_thread(blob.upload_from_string, image_bytes, content_type="image/gif")
        
        return filename
        
    async def cleanup_old_frames(self, max_age_hours: int = 3) -> int:
        """Deletes files in GCS that are older than max_age_hours."""
        import asyncio
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cutoff_time = now - max_age_seconds
        
        def _delete_sync():
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.firebasestorage.app")
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            prefix = f"radar/{self.station_code}/"
            
            blobs = bucket.list_blobs(prefix=prefix)
            deleted_count = 0
            
            for blob in blobs:
                try:
                    base_name = blob.name.split("/")[-1]
                    ts_str = base_name.replace(f"{self.station_code}_", "").replace(".gif", "")
                    blob_ts = int(ts_str)
                    if blob_ts < cutoff_time:
                        blob.delete()
                        deleted_count += 1
                except Exception:
                    pass
            return deleted_count
            
        return await asyncio.to_thread(_delete_sync)
