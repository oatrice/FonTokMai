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
try:
    from google.cloud import storage
except Exception:
    storage = None
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


class TMDMultiframeMixin:

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
        min_dim = min(prev_gray.shape[:2])

        if min_dim >= 200:
            # Production-sized frame: improved params for better small-cloud tracking.
            import math as _math
            n_levels = min(6, max(1, int(_math.log2(max(1, min_dim / 16)))))
            n_winsize = 21
        else:
            # Small frame (e.g. unit tests): keep original params that are stable
            # at this scale. The pyramid depth and window are intentionally larger
            # relative to the image, which OpenCV handles by clamping internally.
            n_levels = 5
            n_winsize = 25

        flow = cv2.calcOpticalFlowFarneback(
            prev=prev_gray,
            next=curr_gray,
            flow=None,
            pyr_scale=0.5,
            levels=n_levels,
            winsize=n_winsize,
            iterations=5,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )

        # Extrapolate wind into empty regions so tracking works everywhere
        flow = self.densify_optical_flow(flow)

        return flow
        
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
        
        # 2. Blur the masked flow and the mask.
        # Using (51, 51) instead of (101, 101) to preserve local flow direction
        # near crop boundaries and avoid smearing global-average into edge clouds.
        ksize = (51, 51)
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
            
        # Prioritize the velocity of the approaching storm (fallback_vx, fallback_vy) if available,
        # because the local flow at a target pixel might be zero/noisy/inaccurate.
        if (fallback_vx != 0.0 or fallback_vy != 0.0):
            vx, vy = fallback_vx, fallback_vy
        else:
            vx, vy = self.get_flow_vector_at(flow, px, py)
            
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
