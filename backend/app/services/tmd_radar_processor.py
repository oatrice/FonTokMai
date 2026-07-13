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
            levels=5,
            winsize=25,
            iterations=5,
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
        
    def generate_multiframe_flow_debug_images(self, frames: List[np.ndarray], user_px: int, user_py: int, min_dbz: float, flow_mode: str = "latest") -> dict:
        """
        Applies optical flow to all consecutive pairs in frames and horizontally concatenates
        the 4 debug views into wide timeline images.
        """
        all_masks = []
        all_hsvs = []
        all_grids = []
        all_clusters = []
        
        for i in range(len(frames) - 1):
            curr_img = frames[i+1]
            if flow_mode == "average":
                flow = self.calculate_average_optical_flow(frames[:i+2])
            else:
                prev_img = frames[i]
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

    def extrapolate_rain_at_pixel(
        self, img: np.ndarray, flow: np.ndarray, px: int, py: int, steps: int,
        rate: float = 0.0, radius: int = 5,
        fallback_vx: float = 0.0, fallback_vy: float = 0.0
    ) -> Tuple[float, int, int]:
        """
        Uses Semi-Lagrangian backward tracking to find the dBZ value that will arrive at (px, py) in 'steps' time intervals.
        Each step corresponds to the time difference between the frames used to compute the optical flow (e.g. 15 mins).
        Positive steps mean predicting into the future.
        If 'rate' is provided, it applies an exponential growth/decay factor per step.
        'radius' is used to search a local neighborhood (e.g. +/- 5 pixels) to account for slight movement inaccuracies and cloud edges.
        """
        if steps == 0:
            return self.get_dbz_at_pixel(img, px, py), px, py
            
        # Get the flow vector at the target pixel
        vx, vy = self.get_flow_vector_at(flow, px, py)
        
        # If local flow is zero/very small, fallback to the velocity of the approaching storm
        if math.hypot(vx, vy) < 0.5 and (fallback_vx != 0.0 or fallback_vy != 0.0):
            vx, vy = fallback_vx, fallback_vy
            
        # Calculate source pixel (backward tracking)
        # Assuming linear constant velocity over the steps
        src_x = int(round(px - (vx * steps)))
        src_y = int(round(py - (vy * steps)))
        
        max_dbz = 0.0
        best_sx = src_x
        best_sy = src_y
        
        # Check a bounding box of +/- radius around the source pixel
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = src_x + dx
                sy = src_y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = self.get_dbz_at_pixel(img, sx, sy)
                    if d > max_dbz:
                        max_dbz = d
                        best_sx = sx
                        best_sy = sy
                        
        dbz = max_dbz
        
        if rate != 0.0 and dbz > 0:
            factor = 1.0 + rate
            if factor <= 0:
                return 0.0, best_sx, best_sy
            dbz *= (factor ** abs(steps))
            
            if dbz > 75.0:
                dbz = 75.0
            elif dbz < 10.0:
                dbz = 0.0
        return float(dbz), best_sx, best_sy

    def calculate_average_optical_flow(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Calculates a temporal-averaged optical flow (Lagrangian) across multiple consecutive frames.
        It computes the optical flow between each consecutive pair, then for each pixel in the 
        latest frame, it traces backwards through time to sum up the velocities along the cloud's path.
        Returns the averaged flow vector for each pixel in the final frame.
        """
        if len(frames) < 2:
            raise ValueError("At least 2 frames required for optical flow")
            
        # Calculate flow for each consecutive pair
        flows = []
        for i in range(len(frames) - 1):
            flows.append(self.calculate_optical_flow([frames[i], frames[i+1]]))
            
        N = len(flows)
        if N == 1:
            return flows[0]
            
        H, W = flows[0].shape[:2]
        Y, X = np.indices((H, W))
        curr_x = X.astype(np.float32)
        curr_y = Y.astype(np.float32)
        
        total_vx = np.zeros((H, W), dtype=np.float32)
        total_vy = np.zeros((H, W), dtype=np.float32)
        
        # Trace backward from the newest frame to the oldest
        for i in range(N - 1, -1, -1):
            # Sample the velocity at the current traced coordinates
            mapped_flow = cv2.remap(flows[i], curr_x, curr_y, interpolation=cv2.INTER_LINEAR)
            vx = mapped_flow[..., 0]
            vy = mapped_flow[..., 1]
            
            total_vx += vx
            total_vy += vy
            
            # Move the coordinates backward in time for the next iteration
            curr_x -= vx
            curr_y -= vy
            
        # Return the temporal average
        avg_flow = np.stack([total_vx / N, total_vy / N], axis=-1)
        return avg_flow

    @staticmethod
    def draw_pin_on_frame(img: np.ndarray, x: int, y: int) -> None:
        """Draws the blue location pin on the image at the specified pixel coordinates."""
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return
            
        overlay = img.copy()
        
        # White halo for contrast
        cv2.circle(overlay, (x, y), radius=14, color=(255, 255, 255), thickness=5)
        cv2.circle(overlay, (x, y), radius=20, color=(255, 255, 255), thickness=3)
        # Blue target body. The frame data is RGB, so this must be RGB blue.
        color = (0, 0, 255)
        cv2.circle(overlay, (x, y), radius=12, color=color, thickness=4)
        cv2.drawMarker(overlay, (x, y), color=color, markerType=cv2.MARKER_CROSS, markerSize=24, thickness=4)
        
        # Apply semi-transparent overlay (alpha = 0.6)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

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
    def render_rain_summary(predictions: list, confidence_cutoff_min: int = 90, time_offset_min: float = 0.0, confidence_score: float = 1.0, approaching_clouds: list = None) -> str:
        """
        Generates a smart, non-redundant rain summary line for Telegram based on the pixel's time-series predictions.
        """
        warning = "\n⚠️ ข้อมูลขาดช่วง (ความแม่นยำต่ำ)" if confidence_score < 1.0 else ""
        
        def fmt_eta(minutes: float) -> str:
            m = int(round(minutes - time_offset_min))
            if m < 0:
                m = 0
            if m < 60:
                return f"~{m} นาที"
            h = m // 60
            r = m % 60
            return f"~{h} ชม. {r} นาที" if r else f"~{h} ชม."

        def dbz_label(dbz: float) -> str:
            if dbz >= 55: return "ฝนหนักมาก"
            if dbz >= 35: return "ฝนหนัก"
            if dbz >= 20: return "ฝนปานกลาง"
            return "ฝนเบา"

        def fmt_clock_time(minutes_offset: float) -> str:
            m = int(round(minutes_offset - time_offset_min))
            if m < 0:
                m = 0
            bkk_now = datetime.now(timezone(timedelta(hours=7)))
            target = bkk_now + timedelta(minutes=m)
            return target.strftime('%H:%M น.')

        if not predictions:
            return f"ℹ️ ไม่สามารถพยากรณ์ล่วงหน้าได้{warning}"

        rain_events = []
        in_rain = False
        start_idx = -1
        max_dbz = 0.0
        max_idx = -1
        
        for i, p in enumerate(predictions):
            dbz = p["dbz"]
            if dbz >= 15.0:
                if not in_rain:
                    in_rain = True
                    start_idx = i
                    max_dbz = dbz
                    max_idx = i
                else:
                    if dbz > max_dbz:
                        max_dbz = dbz
                        max_idx = i
            else:
                if in_rain:
                    in_rain = False
                    rain_events.append({
                        "start_idx": start_idx,
                        "stop_idx": i,
                        "max_dbz": max_dbz,
                        "max_idx": max_idx
                    })
        
        if in_rain:
            rain_events.append({
                "start_idx": start_idx,
                "stop_idx": -1,
                "max_dbz": max_dbz,
                "max_idx": max_idx
            })

        active_event = None
        for event in rain_events:
            stop_idx = event["stop_idx"]
            if stop_idx == -1:
                active_event = event
                break
            
            stop_time = predictions[stop_idx]["time_offset"]
            if stop_time - time_offset_min > 0:
                active_event = event
                break

        if not active_event:
            max_time = predictions[-1]["time_offset"]
            text = f"☀️ ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน {fmt_eta(max_time)}นี้"
            if approaching_clouds:
                far_clouds = [c for c in approaching_clouds if c.get("eta_min", 0) > max_time]
                if far_clouds:
                    soonest = min(far_clouds, key=lambda c: c.get("eta_min", 999))
                    eta_val = max(1.0, float(soonest["eta_min"]) - time_offset_min)
                    eta_h = int(eta_val // 60)
                    eta_m = int(eta_val % 60)
                    time_str = f"~{eta_h} ชม. {eta_m} นาที" if eta_h > 0 else f"~{eta_m} นาที"
                    if eta_h > 0 and eta_m == 0:
                        time_str = f"~{eta_h} ชม."
                    text += f"\n☁️ หมายเหตุ: ตรวจพบกลุ่มฝน ({int(soonest.get('dbz_now', 0))} dBZ) กำลังเคลื่อนมา อาจจะถึงในอีก {time_str} (เวลาประมาณ {fmt_clock_time(float(soonest['eta_min']))})"
            
            return text + warning

        start_idx = active_event["start_idx"]
        stop_idx = active_event["stop_idx"]
        max_dbz = active_event["max_dbz"]
        max_idx = active_event["max_idx"]
        
        start_time = predictions[start_idx]["time_offset"]
        start_dbz = predictions[start_idx]["dbz"]
        lbl_start = dbz_label(start_dbz)
        
        adj_start = start_time - time_offset_min
        
        if adj_start <= 0:
            msg_start = f"🌧️ ฝนกำลังตกอยู่ ({int(start_dbz)} dBZ — {lbl_start})"
            if stop_idx == -1:
                max_time = predictions[-1]["time_offset"]
                msg_duration = f"และคาดว่าจะตกต่อเนื่องถึงอย่างน้อย {fmt_eta(max_time)} (เวลา {fmt_clock_time(max_time)})"
            else:
                stop_time = predictions[stop_idx]["time_offset"]
                msg_duration = f"และคาดว่าจะหยุดตกในอีก {fmt_eta(stop_time)} (เวลาประมาณ {fmt_clock_time(stop_time)})"
        else:
            msg_start = f"⏱ ฝนกำลังจะมาใน {fmt_eta(start_time)} (เวลาประมาณ {fmt_clock_time(start_time)}) ({int(start_dbz)} dBZ — {lbl_start})"
            if stop_idx == -1:
                max_time = predictions[-1]["time_offset"]
                duration = int(max_time - start_time)
                msg_duration = f"และคาดว่าจะตกต่อเนื่องอย่างน้อย {duration} นาที (ถึงอย่างน้อย {fmt_clock_time(max_time)})"
            else:
                stop_time = predictions[stop_idx]["time_offset"]
                duration = int(stop_time - start_time)
                msg_duration = f"และคาดว่าจะตกต่อเนื่องประมาณ {duration} นาที (ถึงเวลาประมาณ {fmt_clock_time(stop_time)})"
        
        if max_idx > start_idx and max_dbz >= start_dbz + 15.0:
            max_time = predictions[max_idx]["time_offset"]
            lbl_max = dbz_label(max_dbz)
            return (
                f"{msg_start}\n"
                f"⚡ และจะตกหนักขึ้นใน {fmt_eta(max_time)} ({int(max_dbz)} dBZ — {lbl_max})\n"
                f"{msg_duration}{warning}"
            )
        else:
            return f"{msg_start}\n{msg_duration}{warning}"

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
    def _resolve_label_collisions(labels, obstacles, img_w, img_h, iterations=30):
        import math
        
        def get_overlap(c1x, c1y, w1, h1, c2x, c2y, w2, h2):
            dx = c1x - c2x
            dy = c1y - c2y
            ox = (w1 + w2) / 2 - abs(dx)
            oy = (h1 + h2) / 2 - abs(dy)
            if ox > 0 and oy > 0:
                return ox, oy, dx, dy
            return 0, 0, dx, dy

        for _ in range(iterations):
            for i, lbl in enumerate(labels):
                fx, fy = 0.0, 0.0
                
                dx_ideal = lbl['ideal_cx'] - lbl['cx']
                dy_ideal = lbl['ideal_cy'] - lbl['cy']
                fx += dx_ideal * 0.1
                fy += dy_ideal * 0.1
                
                margin = lbl.get('margin', 4)
                for obs in obstacles:
                    ox, oy, w, h = obs[0], obs[1], obs[2], obs[3]
                    obs_cx = ox + w / 2
                    obs_cy = oy + h / 2
                    
                    ovx, ovy, dx, dy = get_overlap(
                        lbl['cx'], lbl['cy'], lbl['w'] + margin, lbl['h'] + margin,
                        obs_cx, obs_cy, w, h
                    )
                    
                    if ovx > 0 and ovy > 0:
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dx, dy, dist = 1.0, 1.0, 1.414
                        fx += (dx / dist) * (ovx + ovy) * 0.8
                        fy += (dy / dist) * (ovx + ovy) * 0.8
                
                for j, other in enumerate(labels):
                    if i == j: continue
                    margin_other = other.get('margin', 4)
                    ovx, ovy, dx, dy = get_overlap(
                        lbl['cx'], lbl['cy'], lbl['w'] + margin, lbl['h'] + margin,
                        other['cx'], other['cy'], other['w'] + margin_other, other['h'] + margin_other
                    )
                    if ovx > 0 and ovy > 0:
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dx, dy, dist = 1.0, 1.0, 1.414
                        fx += (dx / dist) * (ovx + ovy) * 0.5
                        fy += (dy / dist) * (ovx + ovy) * 0.5
                
                lbl['cx'] += fx
                lbl['cy'] += fy
                
                lbl['cx'] = max(lbl['w']/2 + 5, min(img_w - lbl['w']/2 - 5, lbl['cx']))
                lbl['cy'] = max(lbl['h']/2 + 5, min(img_h - lbl['h']/2 - 5, lbl['cy']))

    @staticmethod
    def generate_radar_tracking_image(
        frame: np.ndarray,
        user_x: int,
        user_y: int,
        clouds: list,
        time_utc: datetime = None,
        all_rain_clusters: list = None,
        predictions: list = None,
        show_clouds: bool = True,
        show_trajectory: bool = True,
        time_offset_min: float = 0.0
    ) -> Optional[bytes]:
        import math
        display_clouds = clouds or []
        ambient_clouds = [
            c for c in (all_rain_clusters or [])
            if not any(
                math.hypot(c["cx"] - d["cx"], c["cy"] - d["cy"]) < 30
                for d in display_clouds
            )
        ] if all_rain_clusters else []
        
        from app.services.weather_manager import _DEV_CONFIG
        if _DEV_CONFIG.get("verbose"):
            logger.info(f"[TRACKING_IMG] Preparing to draw. display_clouds={len(display_clouds)}, ambient_clouds={len(ambient_clouds)}")
        
        if frame is None or (not display_clouds and not ambient_clouds):
            return None

        crop_r = 120
        h, w = frame.shape[:2]
        x1 = max(0, user_x - crop_r)
        y1 = max(0, user_y - crop_r)
        x2 = min(w, user_x + crop_r)
        y2 = min(h, user_y + crop_r)
        
        crop_img = frame[y1:y2, x1:x2].copy()
        scale = 3.0
        
        img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        ux = int((user_x - x1) * scale)
        uy = int((user_y - y1) * scale)
        
        def _dbz_color(dbz):
            if dbz >= 60: return (155, 89, 182)
            elif dbz >= 50: return (231, 76, 60)
            elif dbz >= 40: return (243, 156, 18)
            elif dbz >= 30: return (241, 196, 15)
            else: return (46, 204, 113)

        obstacles = []
        labels = []
        
        obstacles.append((ux - int(12 * scale), uy - int(12 * scale), int(24 * scale), int(24 * scale)))
        
        has_predicted_rain = predictions and any(p.get("dbz", 0) >= 10.0 for p in predictions)
        if show_trajectory and predictions and has_predicted_rain:
            pts = []
            for p in predictions:
                px_pred = p["src_x"]
                py_pred = p["src_y"]
                cx = int((px_pred - x1) * scale)
                cy = int((py_pred - y1) * scale)
                pts.append((cx, cy, p))
            
            if len(pts) > 1:
                last_labeled_pt = None
                for i, (cx, cy, p) in enumerate(pts):
                    dbz_val = p.get("dbz", 0.0)
                    dot_color = _dbz_color(dbz_val) if dbz_val >= 10.0 else (200, 200, 200)
                    cv2.circle(img, (cx, cy), int(3.5 * scale), (0, 0, 0), -1)
                    cv2.circle(img, (cx, cy), int(2.2 * scale), dot_color, -1)
                    obstacles.append((cx - int(2 * scale), cy - int(2 * scale), int(4 * scale), int(4 * scale)))
                    
                    if i > 0:
                        prev_cx, prev_cy, _ = pts[i-1]
                        cv2.line(img, (prev_cx, prev_cy), (cx, cy), (0, 255, 255), int(1.2 * scale))
                        
                    eta = p.get("time_offset", 0)
                    should_label = False  # Disabled trajectory text (15m, 90m) as requested
                    # if eta > 0 and (i == 1 or i == len(pts)-1 or (eta % 45 == 0)):
                    #     if last_labeled_pt is None:
                    #         should_label = True
                    #     else:
                    #         if math.hypot(cx - last_labeled_pt[0], cy - last_labeled_pt[1]) > 30 * scale:
                    #             should_label = True
                    # 
                    # if i == len(pts) - 1 and not should_label:
                    #     if last_labeled_pt is None or math.hypot(cx - last_labeled_pt[0], cy - last_labeled_pt[1]) > 10 * scale:
                    #         should_label = True
                    #         
                    # if should_label:
                    #     txt = f"{eta}m"
                    #     tw, th = int(35 * scale), int(12 * scale)
                    #     if cx < ux:
                    #         tx = cx - tw - int(8 * scale)
                    #     else:
                    #         tx = cx + int(12 * scale)
                    #     ty = cy - int(16 * scale)
                    #     
                    #     labels.append({
                    #         'text': txt,
                    #         'type': 'trajectory',
                    #         'margin': 12 * scale,
                    #         'w': tw, 'h': th,
                    #         'cx': tx + tw/2,
                    #         'cy': ty - th/2,
                    #         'ideal_cx': tx + tw/2,
                    #         'ideal_cy': ty - th/2,
                    #         'anchor_x': cx,
                    #         'anchor_y': cy,
                    #         'scale': 0.35 * scale,
                    #         'fg': (255, 255, 255),
                    #         'bg': (0, 0, 0)
                    #     })
                    #     last_labeled_pt = (cx, cy)
        
        if show_clouds:
            incoming = [c for c in display_clouds if c.get("approaching", False) and -120 <= c.get("eta_min", 9999) <= 180]
            incoming.sort(key=lambda c: c.get("predicted_dbz", 0), reverse=True)
            
            for c_orig in incoming[:3]:
                cx_orig, cy_orig = c_orig["cx"], c_orig["cy"]
                cx = int((cx_orig - x1) * scale)
                cy = int((cy_orig - y1) * scale)
                dbz = c_orig.get("predicted_dbz", c_orig.get("dbz_now", 20))
                vx, vy = c_orig.get("vx", 0), c_orig.get("vy", 0)
                
                color = _dbz_color(dbz)
                hull_rect = None
                if "pixels" in c_orig and len(c_orig["pixels"]) > 2:
                    pts = np.array([[(int((px - x1) * scale), int((py - y1) * scale))] for px, py in c_orig["pixels"]], dtype=np.int32)
                    hull = cv2.convexHull(pts)
                    hull_rect = cv2.boundingRect(hull)
                    overlay = img.copy()
                    cv2.fillPoly(overlay, [hull], color)
                    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
                    cv2.polylines(img, [hull], True, color, max(1, int(2.0 * scale)))
                    obstacles.append((hull_rect[0]-5, hull_rect[1]-5, hull_rect[2]+10, hull_rect[3]+10))
                else:
                    r = int(12 * scale)
                    cv2.circle(img, (cx, cy), r, color, int(1.5 * scale))
                    obs_r = int(14 * scale)
                    obstacles.append((cx-obs_r, cy-obs_r, 2*obs_r, 2*obs_r))
                
                vx_s = int(vx * scale * 3.0)
                vy_s = int(vy * scale * 3.0)
                arrow_sx, arrow_sy = cx, cy
                if hull_rect:
                    arrow_sx = hull_rect[0] + hull_rect[2] // 2
                    arrow_sy = hull_rect[1] + hull_rect[3] // 2
                
                if vx_s == 0 and vy_s == 0:
                    cv2.arrowedLine(img, (arrow_sx, arrow_sy), (ux, uy), (255, 255, 0), int(1.5 * scale), tipLength=0.15)
                else:
                    cv2.arrowedLine(img, (arrow_sx, arrow_sy), (arrow_sx + vx_s, arrow_sy + vy_s), (255, 255, 0), int(1.5 * scale), tipLength=0.3)
                    
                eta = max(1.0, float(c_orig.get("eta_min", 0)) - time_offset_min)
                if eta <= 0:
                    txt = f"{c_orig.get('label', '')} (Now)"
                else:
                    abs_eta = int(abs(eta))
                    time_str = f"{abs_eta}m" if abs_eta < 60 else f"{abs_eta//60}h{abs_eta%60}m"
                    txt = f"{c_orig.get('label', '')}: ~{time_str}"
                    
                tw, th = int(55 * scale), int(15 * scale)
                tx = arrow_sx - int(tw / 2)
                if hull_rect:
                    ty = hull_rect[1] - int(10 * scale) - th
                else:
                    ty = arrow_sy - int(20 * scale) - th
                
                labels.append({
                    'text': txt,
                    'type': 'approaching',
                    'margin': 8 * scale,
                    'w': tw, 'h': th,
                    'cx': tx + tw/2,
                    'cy': ty - th/2,
                    'ideal_cx': tx + tw/2,
                    'ideal_cy': ty - th/2,
                    'anchor_x': arrow_sx,
                    'anchor_y': arrow_sy,
                    'scale': 0.45 * scale,
                    'fg': (255, 255, 255),
                    'bg': (0, 0, 0)
                })

            ambient_clouds.sort(key=lambda c: c.get("dist", 9999))
            for c_orig in ambient_clouds[:8]:
                cx_orig, cy_orig = c_orig["cx"], c_orig["cy"]
                if cx_orig < x1 - 80 or cx_orig > x2 + 80 or cy_orig < y1 - 80 or cy_orig > y2 + 80:
                    continue
                cx = int((cx_orig - x1) * scale)
                cy = int((cy_orig - y1) * scale)
                dbz = c_orig.get("predicted_dbz", c_orig.get("dbz_now", 20))
                vx, vy = c_orig.get("vx", 0), c_orig.get("vy", 0)
                
                color = _dbz_color(dbz)
                for angle_deg in range(0, 360, 30):
                    a1 = math.radians(angle_deg)
                    a2 = math.radians(angle_deg + 20)
                    r = int(10 * scale)
                    p1 = (int(cx + r * math.cos(a1)), int(cy + r * math.sin(a1)))
                    p2 = (int(cx + r * math.cos(a2)), int(cy + r * math.sin(a2)))
                    cv2.line(img, p1, p2, color, int(scale * 0.8))
                obs_r = int(10 * scale)
                obstacles.append((cx-obs_r, cy-obs_r, 2*obs_r, 2*obs_r))
                
                vx_s = int(vx * scale * 2.5)
                vy_s = int(vy * scale * 2.5)
                v_mag = math.hypot(vx_s, vy_s)
                if v_mag > 2:
                    cv2.arrowedLine(img, (cx, cy), (cx + vx_s, cy + vy_s), (200, 200, 200), max(1, int(scale * 0.8)), tipLength=0.3)
                    
                txt = f"{c_orig.get('label', '')}: {int(dbz)}"
                tw, th = int(45 * scale), int(12 * scale)
                tx = cx - int(tw / 2)
                ty = cy - int(16 * scale) - th
                
                labels.append({
                    'text': txt,
                    'type': 'ambient',
                    'margin': 0,
                    'w': tw, 'h': th,
                    'cx': tx + tw/2,
                    'cy': ty - th/2,
                    'ideal_cx': tx + tw/2,
                    'ideal_cy': ty - th/2,
                    'anchor_x': cx,
                    'anchor_y': cy,
                    'scale': 0.4 * scale,
                    'fg': (200, 200, 200),
                    'bg': (0, 0, 0)
                })

        hit_r = int(_DEV_CONFIG.get("hit_radius", 8) * scale)
        for angle_deg in range(0, 360, 15):
            a1 = math.radians(angle_deg)
            a2 = math.radians(angle_deg + 8)
            p1 = (int(ux + hit_r * math.cos(a1)), int(uy + hit_r * math.sin(a1)))
            p2 = (int(ux + hit_r * math.cos(a2)), int(uy + hit_r * math.sin(a2)))
            cv2.line(img, p1, p2, (0, 165, 255), int(1.2 * scale))
            
        cv2.circle(img, (ux, uy), radius=int(6 * scale), color=(255, 255, 255), thickness=int(3 * scale))
        cv2.drawMarker(img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(10 * scale), int(3 * scale))

        TMDRadarProcessor._resolve_label_collisions(labels, obstacles, img.shape[1], img.shape[0])

        for t_lbl in labels:
            if t_lbl.get('type') == 'trajectory':
                for a_lbl in labels:
                    if a_lbl.get('type') == 'approaching':
                        dx = abs(t_lbl['cx'] - a_lbl['cx'])
                        dy = abs(t_lbl['cy'] - a_lbl['cy'])
                        if dx < (t_lbl['w'] + a_lbl['w']) / 2 + 4 * scale and dy < (t_lbl['h'] + a_lbl['h']) / 2 + 4 * scale:
                            t_lbl['hidden'] = True
                            break

        for lbl in labels:
            if lbl.get('hidden'):
                continue
            tx = int(lbl['cx'] - lbl['w']/2)
            ty = int(lbl['cy'] + lbl['h']/2)
            
            dist_to_anchor = math.hypot(lbl['cx'] - lbl['anchor_x'], lbl['cy'] - lbl['anchor_y'])
            if dist_to_anchor > 12 * scale:
                cv2.line(img, (lbl['anchor_x'], lbl['anchor_y']), (int(lbl['cx']), int(lbl['cy'])), (150, 150, 150), max(2, int(scale * 1.0)))
                
            cv2.putText(img, lbl['text'], (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, lbl['scale'], lbl['bg'], max(1, int(lbl['scale'] * 5.0)))
            cv2.putText(img, lbl['text'], (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, lbl['scale'], lbl['fg'], max(1, int(lbl['scale'] * 1.8)))

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

        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        is_success, buffer = cv2.imencode(".png", img_bgr)
        return buffer.tobytes() if is_success else None

    @staticmethod
    def generate_timeline_image(predictions: list, location_name: str = None) -> Optional[bytes]:
        if not predictions:
            return None
        try:
            import io
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

        last_x = -999
        y_offsets = {}

        for i, p in enumerate(predictions):
            eta = p["time_offset"]
            dbz = p["dbz"]
            
            # Estimate growth relative to previous step
            if i > 0 and predictions[i-1]["dbz"] > 0:
                growth = (dbz - predictions[i-1]["dbz"]) / predictions[i-1]["dbz"]
            elif i > 0 and dbz > 0 and predictions[i-1]["dbz"] == 0:
                growth = 1.0 # 100% growth (new rain)
            else:
                growth = 0.0

            x = time_to_x(eta)
            x = max(20, min(780, x))

            h = int(dbz * 4)

            if dbz >= 60: color = (155, 89, 182, 230)   # Purple
            elif dbz >= 50: color = (231, 76, 60, 230)  # Red
            elif dbz >= 40: color = (243, 156, 18, 230) # Orange
            elif dbz >= 30: color = (241, 196, 15, 230) # Yellow
            elif dbz > 0: color = (46, 204, 113, 230)   # Green
            else: color = (100, 100, 100, 100)          # Grey/Clear for 0 dBz

            if eta > 90:
                color = (color[0], color[1], color[2], 100)

            if dbz > 0:
                draw.rectangle([(x-10, baseline_y-h), (x+10, baseline_y)], fill=color)
            
            cluster_label = p.get("cluster")
            if cluster_label:
                draw.text((x-12, baseline_y-h-35), f"[{cluster_label}]", fill=(150, 200, 255, 255), font=font_small)
            
            if dbz > 0:
                draw.text((x-12, baseline_y-h-20), f"{int(dbz)}", fill=(255, 255, 255, 255), font=font)

            # ── Growth / decay trend arrow ─────────────────────────────────
            arrow_y_base = baseline_y - h - 35 if cluster_label else baseline_y - h - 22
            growth_pct = growth * 100.0
            
            if dbz > 0:
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
            else:
                # 0 dBz: Clear sky indicator instead of arrows
                draw.text((x-15, arrow_y_base - 12), "Clear", fill=(120, 120, 120, 180), font=font_small)

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

        if location_name:
            loc_text = f"พิกัด: {location_name}"
            # text length roughly
            text_bbox = draw.textbbox((0, 0), loc_text, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            draw.text((width - text_w - 20, 20), loc_text, fill=(200, 200, 200, 255), font=font)

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
        import time
        prefix = self.station_code[:3]
        php_url = f"https://weather.tmd.go.th/{prefix}.php?t={int(time.time())}"
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
        import time
        url = f"{self.config.static_image_url}?t={int(time.time())}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.warning(f"[{self.station_code}] Failed to fetch static image: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"[{self.station_code}] Exception in fetch_latest_image_bytes: {e}", exc_info=True)
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
        import time
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
            url = f"{url}?t={int(time.time())}"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        loop_bytes = response.content
                        last_modified = response.headers.get("last-modified")
                        
                        try:
                            php_url = f"https://weather.tmd.go.th/{self.station_code[:3]}.php?t={int(time.time())}"
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
                logger.error(f"[{self.station_code}] Error fetching loop gif: {e}")

                
        if loop_bytes:
            # Validate magic bytes: TMD server sometimes returns non-GIF content
            # (HTML error pages, empty bodies) which causes Pillow/OpenCV to crash.
            if not (loop_bytes[:6] in (b"GIF87a", b"GIF89a")):
                logger.warning(
                    f"[{self.station_code}] Loop GIF bytes are not a valid GIF image "
                    f"(magic={loop_bytes[:6]!r}, size={len(loop_bytes)}). Skipping frame extraction."
                )
                return [], None, None

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
                    logger.warning(f"[{self.station_code}] Error in OCR timestamp extraction: {e}")

                return frames, dt, loop_bytes
            except Exception as e:
                logger.error(f"[{self.station_code}] Error processing loop gif: {e}")
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

    async def update_radar_cache(self, force: bool = False) -> dict:
        """
        Fetch from TMD and update cache if new image is available or if cache is stale.
        This encapsulates the fetching, OCR, cache validation, loop GIF fallback, and database persistence.
        """
        import os
        import time
        import cv2
        import numpy as np
        from datetime import datetime, timezone
        from app.dependencies import get_repo_context
        from app.services.ocr_service import OCRService

        station = self.station_code
        result = {"station": station, "updated": False, "error": None}
        now_ts = int(datetime.now(timezone.utc).timestamp())

        # 1. Check cache first (for smart polling skip)
        async with get_repo_context() as repo:
            cache = await repo.get_latest_radar_cache(station)
            
        frames = cache.get("frames", []) if cache else []
        latest_ts = frames[0]["timestamp"] if frames else 0
        last_gif_fallback_time = cache.get("last_gif_fallback_time", 0.0) if cache else 0.0

        # Sanity-check: if latest_ts is in the future (e.g. corrupted wall-clock fallback),
        # reset to 0 so a fresh valid OCR timestamp can replace it.
        if latest_ts > now_ts + 300:
            logger.warning(
                f"[{station}] ⚠️ Firestore latest_ts={latest_ts} is in the future "
                f"(now={now_ts}, delta={latest_ts - now_ts}s) — resetting to 0 to unblock cache"
            )
            latest_ts = 0

        # Skip fetch if cache is fresh, has enough frames, and force is False
        if not force and len(frames) >= 2 and (now_ts - latest_ts) < 1200:
            logger.debug(f"[{station}] Cache is fresh (latest_ts={latest_ts}, age={now_ts - latest_ts}s). Skipping update.")
            result["reason"] = "fresh"
            return result

        # 2. Fetch static image bytes
        static_bytes = await self.fetch_latest_image_bytes()
        
        ocr_svc = OCRService()
        ts = None
        frame = None
        np_arr = None

        if static_bytes:
            np_arr = np.frombuffer(static_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            logger.info(f"[{station}] ✅ Static fetch OK — {len(static_bytes):,} bytes, shape={frame.shape[:2]}")
            ts = await ocr_svc.get_frame_timestamp(frame, fallback_ts=now_ts)
            ocr_ok = ts is not None and ts != now_ts
            if not ocr_ok:
                logger.warning(f"[{station}] ⚠️ OCR failed — frame will NOT be saved to avoid corrupting sliding window")
                ts = None
        else:
            logger.warning(f"[{station}] ❌ Static fetch FAILED — will attempt GIF fallback if enabled")

        needs_fallback = False
        fallback_reason = ""

        # Check fallback settings
        async with get_repo_context() as repo:
            sys_settings = await repo.get_system_settings()
        enable_fallback_db = sys_settings.get("enable_gif_fallback", True)
        enable_fallback_env = os.environ.get("ENABLE_TMD_GIF_FALLBACK", "true").lower() == "true"
        enable_fallback = enable_fallback_db and enable_fallback_env

        if enable_fallback:
            if frames:
                gap_to_now = (now_ts - latest_ts) / 60.0
                is_static_outdated = False
                if ts:
                    static_age_minutes = (now_ts - ts) / 60.0
                    if static_age_minutes > 120.0:
                        is_static_outdated = True
                        
                if gap_to_now > 60.0 and (now_ts - last_gif_fallback_time) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Static dead for {gap_to_now:.1f}m"
                elif is_static_outdated and (now_ts - last_gif_fallback_time) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Static image is outdated by {static_age_minutes:.1f}m"
                elif ts and (ts - latest_ts) > 1800.0:
                    needs_fallback = True
                    fallback_reason = f"Large time gap detected ({int((ts - latest_ts)/60)}m) between {latest_ts} and {ts}"
            else:
                if (now_ts - last_gif_fallback_time) > 1800.0:
                    needs_fallback = True
                    fallback_reason = "Cache is empty"

        if enable_fallback and not needs_fallback and len(frames) < 2:
            if (now_ts - last_gif_fallback_time) > 1800.0:
                needs_fallback = True
                fallback_reason = f"Cache has <2 frames ({len(frames)})"

        # If not outdated/dead and unchanged, return early
        if not needs_fallback and ((ts and ts <= latest_ts) or not static_bytes):
            logger.debug(f"[{station}] Image unchanged or unavailable (ts {ts}). Skipping.")
            result["reason"] = "unchanged"
            return result

        new_url = None
        if ts and ts > latest_ts:
            logger.info(f"[{station}] 🆕 New frame detected (ts={ts} > latest={latest_ts}) — saving to GCS")
            new_url = await self.save_polled_frame(static_bytes)
            frames.insert(0, {"url": new_url, "timestamp": ts})
            frames = sorted(frames, key=lambda f: f["timestamp"])
            frames.reverse() # newest first

        if needs_fallback:
            logger.warning(f"[{station}] GIF fallback triggered: {fallback_reason}")
            last_gif_fallback_time = now_ts
            fallback_frames_data, fallback_dt, loop_bytes = await self.fetch_loop_gif_and_extract_frames()
            if fallback_frames_data and len(fallback_frames_data) >= 2:
                logger.info(f"[{station}] 🌀 GIF fallback: fetched {len(fallback_frames_data)} frames")
                recent_fallback = fallback_frames_data[-6:]
                recent_fallback.reverse()

                new_frames_list = []
                base_ts = ts if ts else now_ts
                for i, f_img in enumerate(recent_fallback):
                    f_ts = await ocr_svc.get_frame_timestamp(f_img, fallback_ts=base_ts - i * 900)
                    if f_img.shape[0] != 800 or f_img.shape[1] != 800:
                        f_img = cv2.resize(f_img, (800, 800), interpolation=cv2.INTER_NEAREST)
                    is_success, buffer = cv2.imencode(".png", cv2.cvtColor(f_img, cv2.COLOR_RGB2BGR))
                    if is_success:
                        f_url = await self.save_polled_frame(buffer.tobytes())
                        new_frames_list.append({"url": f_url, "timestamp": f_ts})

                if new_frames_list:
                    gif_newest_ts = new_frames_list[0]["timestamp"]
                    current_newest_ts = frames[0]["timestamp"] if frames else 0
                    is_bootstrap = fallback_reason.startswith("Cache has <2") or fallback_reason == "Cache is empty"

                    if is_bootstrap:
                        if ts and ts > gif_newest_ts:
                            new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                        frames = new_frames_list
                    elif gif_newest_ts > current_newest_ts + 300:
                        logger.info(f"[{station}] GIF data is newer. Adopting GIF frames.")
                        if ts and ts > gif_newest_ts:
                            new_frames_list.insert(0, {"url": new_url, "timestamp": ts})
                        frames = new_frames_list
                    else:
                        logger.warning(f"[{station}] GIF data is NOT newer. Discarding GIF.")

        frames = frames[:6]
        
        async with get_repo_context() as repo:
            await repo.set_latest_radar_cache(
                station_code=station,
                frames=frames,
                last_gif_fallback_time=last_gif_fallback_time
            )
        logger.info(f"Updated cache for {station} with {len(frames)} frames, latest ts {ts}")

        # Cleanup old frames
        deleted = await self.cleanup_old_frames(max_age_hours=3)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old frames for {station}")

        result["updated"] = True
        return result

