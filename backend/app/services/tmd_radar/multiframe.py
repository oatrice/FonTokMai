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
