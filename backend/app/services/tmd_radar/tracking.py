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


class TMDTrackingMixin:

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
        time_offset_min: float = 0.0,
        locked_target_id: Optional[str] = None,
        locked_target_cx: Optional[int] = None,
        locked_target_cy: Optional[int] = None
    ) -> Optional[bytes]:
        import math

        def _resolve_locked_cluster(clusters: list) -> Optional[dict]:
            """Pick the cluster that corresponds to the manually-locked target.

            Prefer position-based matching using the stored lock pixel, because
            cluster labels are reassigned every forecast round (sorted by
            distance), so a grid label like "G5" will never match a cluster
            label "A"/"B"/... . Falls back to label equality if no stored pixel
            is available (legacy locks).
            """
            if not locked_target_id:
                return None
            if locked_target_cx is not None and locked_target_cy is not None:
                best: Optional[dict] = None
                best_dist = float("inf")
                
                is_grid_cell = False
                cell_center_x, cell_center_y = None, None
                if locked_target_id:
                    import re
                    m = re.match(r"^([a-hA-H])[-_]?([1-8])$", locked_target_id)
                    if m:
                        is_grid_cell = True
                        col_char = m.group(1).upper()
                        row_char = m.group(2)
                        grid_col_idx = ord(col_char) - ord('A')
                        grid_row_idx = int(row_char) - 1
                        
                        crop_r = 120
                        crop_x1 = max(0, user_x - crop_r)
                        crop_y1 = max(0, user_y - crop_r)
                        frame_h, frame_w = frame.shape[:2]
                        crop_x2 = min(frame_w, user_x + crop_r)
                        crop_y2 = min(frame_h, user_y + crop_r)
                        cell_w = (crop_x2 - crop_x1) / 8.0
                        cell_h = (crop_y2 - crop_y1) / 8.0
                        cell_center_x = int(crop_x1 + (grid_col_idx + 0.5) * cell_w)
                        cell_center_y = int(crop_y1 + (grid_row_idx + 0.5) * cell_h)
                        
                        cell_x_min = crop_x1 + grid_col_idx * cell_w - 5.0
                        cell_x_max = crop_x1 + (grid_col_idx + 1) * cell_w + 5.0
                        cell_y_min = crop_y1 + grid_row_idx * cell_h - 5.0
                        cell_y_max = crop_y1 + (grid_row_idx + 1) * cell_h + 5.0

                for c in clusters:
                    dist = math.hypot(c["cx"] - locked_target_cx, c["cy"] - locked_target_cy)
                    
                    if is_grid_cell and (cell_x_min <= locked_target_cx <= cell_x_max and cell_y_min <= locked_target_cy <= cell_y_max):
                        if not (cell_x_min <= c["cx"] <= cell_x_max and cell_y_min <= c["cy"] <= cell_y_max):
                            continue
                            
                    if dist < best_dist:
                        best_dist = dist
                        best = c
                # 60px in the full frame is generous enough to follow a moving
                # cloud between frames, but tight enough to avoid snapping to
                # a different nearby cluster in dense areas (~3x the crop scale).
                if best and best_dist <= 60:
                    return best
                return None
            # Legacy fallback for locks that only stored a cluster label.
            for c in clusters:
                if c.get("label") == locked_target_id:
                    return c
            return None

        display_clouds = clouds or []

        # Pre-compute which clouds will be drawn in the "incoming" contour style (eta <= 180 min).
        # This must happen BEFORE building ambient_clouds so the dedup is scoped only to
        # actually-drawn clouds, not the full display_clouds list.
        # BUG-FIX: previously ambient_clouds deduped against ALL display_clouds, which caused
        # far-approaching clusters (eta > 180) to be invisible in both incoming AND ambient.
        _incoming_pre = [
            c for c in display_clouds
            if c.get("approaching", False) and -120 <= c.get("eta_min", 9999) <= 180
        ]
        _incoming_pre.sort(key=lambda c: c.get("predicted_dbz", 0), reverse=True)
        _drawn_clouds = _incoming_pre[:3]  # The up-to-3 clouds rendered with full contour/circle

        ambient_clouds = [
            c for c in (all_rain_clusters or [])
            if not any(
                math.hypot(c["cx"] - d["cx"], c["cy"] - d["cy"]) < 30
                for d in _drawn_clouds  # only exclude clusters already drawn in contour style
            )
        ] if all_rain_clusters else []

        # Far-approaching clouds (eta > 180 min) are excluded from incoming by the eta cap
        # but must still appear in the image to match the text summary. Inject them into
        # ambient_clouds so they render with the dashed-circle style and their label.
        far_approaching = [
            c for c in display_clouds
            if c.get("approaching", False) and c.get("eta_min", 9999) > 180
        ]
        for fc in far_approaching:
            if not any(math.hypot(fc["cx"] - a["cx"], fc["cy"] - a["cy"]) < 30 for a in ambient_clouds):
                ambient_clouds.append(fc)

        from app.services.weather_manager import _DEV_CONFIG
        logger.info(
            f"[TRACKING_IMG] drawn_incoming={[c.get('label') for c in _drawn_clouds]}, "
            f"ambient={[c.get('label') for c in ambient_clouds]}, "
            f"far_approaching={[c.get('label') for c in far_approaching]}"
        )
        if _DEV_CONFIG.get("verbose"):
            logger.info(f"[TRACKING_IMG] display_clouds={len(display_clouds)}, ambient_clouds={len(ambient_clouds)}, far_approaching={len(far_approaching)}")
        
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
            # Re-use the pre-computed list (avoids redundant sort)
            incoming = _incoming_pre

            all_cloud_refs = list(incoming[:3]) + list(ambient_clouds)
            locked_cluster = _resolve_locked_cluster(all_cloud_refs)

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
                    x, y, w, h = cv2.boundingRect(pts)
                    margin = 2
                    mask_w, mask_h = w + 2 * margin, h + 2 * margin
                    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
                    
                    local_pts = pts - np.array([[[x - margin, y - margin]]], dtype=np.int32)
                    for pt in local_pts:
                        px, py = pt[0]
                        if 0 <= px < mask_w and 0 <= py < mask_h:
                            mask[py, px] = 255
                            
                    # Use a slightly smaller kernel to prevent merging distinct cloud chunks
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                    
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    global_contours = []
                    for ctr in contours:
                        # Filter out extremely small noise points
                        if cv2.contourArea(ctr) < 5 and len(ctr) < 3:
                            continue
                            
                        # Use approxPolyDP instead of convexHull to wrap closely and cleanly
                        # around the concave shapes of the individual cloud chunks (Issue #175)
                        epsilon = 0.02 * cv2.arcLength(ctr, True)
                        approx = cv2.approxPolyDP(ctr, epsilon, True)
                        
                        global_ctr = approx + np.array([[[x - margin, y - margin]]], dtype=np.int32)
                        global_contours.append(global_ctr)
                        
                    overlay = img.copy()
                    cv2.fillPoly(overlay, global_contours, color)
                    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
                    cv2.polylines(img, global_contours, True, color, max(1, int(2.0 * scale)))
                    hull_rect = (x, y, w, h)
                    obstacles.append((x - 5, y - 5, w + 10, h + 10))
                else:
                    r = int(12 * scale)
                    cv2.circle(img, (cx, cy), r, color, int(1.5 * scale))
                    obs_r = int(14 * scale)
                    obstacles.append((cx-obs_r, cy-obs_r, 2*obs_r, 2*obs_r))

                is_locked = locked_cluster is not None and c_orig is locked_cluster
                if is_locked:
                    cv2.circle(img, (cx, cy), int(22 * scale), (0, 0, 255), int(2 * scale))
                    cv2.drawMarker(img, (cx, cy), (0, 0, 255), cv2.MARKER_TILTED_CROSS, int(30 * scale), int(2 * scale))
                    
                    # Draw a direct green line-of-sight path from locked cloud (cx, cy) to user (ux, uy)
                    dist_to_user = math.hypot(ux - cx, uy - cy)
                    if dist_to_user > 10:
                        num_dots = int(dist_to_user / 8)
                        for d_idx in range(1, num_dots):
                            t = d_idx / num_dots
                            dot_x = int(cx + (ux - cx) * t)
                            dot_y = int(cy + (uy - cy) * t)
                            cv2.circle(img, (dot_x, dot_y), int(1 * scale), (0, 255, 0), -1)
                            
                    if (vx != 0.0 or vy != 0.0):
                        proj_pts = []
                        for step in range(1, 7):
                            px_proj = cx_orig + vx * step
                            py_proj = cy_orig + vy * step
                            c_proj_x = int((px_proj - x1) * scale)
                            c_proj_y = int((py_proj - y1) * scale)
                            proj_pts.append((c_proj_x, c_proj_y))
                        
                        for i in range(len(proj_pts)):
                            cv2.circle(img, proj_pts[i], int(2 * scale), (0, 0, 255), -1)
                            if i > 0:
                                cv2.line(img, proj_pts[i-1], proj_pts[i], (0, 0, 255), int(1 * scale))
                            else:
                                cv2.line(img, (cx, cy), proj_pts[0], (0, 0, 255), int(1 * scale))

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
                    
                lbl = c_orig.get("label", "")
                if is_locked:
                    # Show the user-facing lock label (e.g. "G5") rather than the
                    # re-assigned cluster label (e.g. "B").
                    lbl = f"LOCKED[{locked_target_id}]"
                eta = max(1.0, float(c_orig.get("eta_min", 0)) - time_offset_min)
                if eta <= 0:
                    txt = f"{lbl} (Now)"
                else:
                    abs_eta = int(abs(eta))
                    time_str = f"{abs_eta}m" if abs_eta < 60 else f"{abs_eta//60}h{abs_eta%60}m"
                    txt = f"{lbl}: ~{time_str}"
                    
                tw, th = int(65 * scale) if is_locked else int(55 * scale), int(15 * scale)
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
                    'fg': (0, 0, 255) if is_locked else (255, 255, 255),
                    'bg': (255, 255, 255) if is_locked else (0, 0, 0)
                })

            # Sort and build list of ambient clouds to render, prioritizing the locked target
            ambient_clouds.sort(key=lambda c: c.get("dist", 9999))
            rendered_ambient = []
            if locked_cluster is not None and locked_cluster in ambient_clouds:
                rendered_ambient.append(locked_cluster)
            for c in ambient_clouds:
                if len(rendered_ambient) >= 8:
                    break
                if c not in rendered_ambient:
                    rendered_ambient.append(c)

            # ── Debug log: show every ambient cloud's centroid vs peak ──────────────
            for _c in rendered_ambient:
                _lbl  = _c.get('label', '?')
                _ccx  = _c.get('cx', -1)
                _ccy  = _c.get('cy', -1)
                _pcx  = _c.get('peak_cx', _ccx)
                _pcy  = _c.get('peak_cy', _ccy)
                _dist = _c.get('dist', -1)
                _npx  = len(_c.get('pixels', []))
                _dbz  = _c.get('dbz_now', -1)
                _drift = math.hypot(_pcx - _ccx, _pcy - _ccy)
                logger.info(
                    f"[AMBIENT_DBG] lbl={_lbl} centroid=({_ccx},{_ccy}) "
                    f"peak=({_pcx},{_pcy}) drift={_drift:.1f}px "
                    f"pixels={_npx} dbz={_dbz:.1f} dist_to_user={_dist:.1f}"
                )

            for c_orig in rendered_ambient:
                cx_orig, cy_orig = c_orig["cx"], c_orig["cy"]
                if cx_orig < x1 - 80 or cx_orig > x2 + 80 or cy_orig < y1 - 80 or cy_orig > y2 + 80:
                    continue

                # Centroid position — used for ETA/arrow/projection (computation-stable)
                cx = int((cx_orig - x1) * scale)
                cy = int((cy_orig - y1) * scale)

                # Peak-dBZ position — used for the dashed-circle marker and label anchor
                # so the circle lands on the convective core, not the weighted centroid.
                # Falls back to centroid for far_approaching clouds that lack peak_cx.
                peak_cx_orig = c_orig.get("peak_cx", cx_orig)
                peak_cy_orig = c_orig.get("peak_cy", cy_orig)
                pcx = int((peak_cx_orig - x1) * scale)
                pcy = int((peak_cy_orig - y1) * scale)

                dbz = c_orig.get("predicted_dbz", c_orig.get("dbz_now", 20))
                vx, vy = c_orig.get("vx", 0), c_orig.get("vy", 0)

                color = _dbz_color(dbz)
                # Draw dashed circle at PEAK (brightest pixel) position
                for angle_deg in range(0, 360, 30):
                    a1 = math.radians(angle_deg)
                    a2 = math.radians(angle_deg + 20)
                    r = int(10 * scale)
                    p1 = (int(pcx + r * math.cos(a1)), int(pcy + r * math.sin(a1)))
                    p2 = (int(pcx + r * math.cos(a2)), int(pcy + r * math.sin(a2)))
                    cv2.line(img, p1, p2, color, int(scale * 0.8))
                # Obstacle bounding box at centroid (stable for label collision avoidance)
                obs_r = int(10 * scale)
                obstacles.append((cx-obs_r, cy-obs_r, 2*obs_r, 2*obs_r))

                # ── Visual debug overlay (verbose=True) ──────────────────────────
                if _DEV_CONFIG.get("verbose"):
                    _lbl_d = c_orig.get('label', '?')
                    # Yellow dot = weighted centroid
                    cv2.circle(img, (cx, cy), int(4 * scale), (0, 255, 255), -1)
                    # Red dot = peak dBZ pixel
                    cv2.circle(img, (pcx, pcy), int(4 * scale), (0, 0, 255), -1)
                    # Cyan line: centroid → peak  (shows how far apart they are)
                    if (pcx, pcy) != (cx, cy):
                        cv2.line(img, (cx, cy), (pcx, pcy), (255, 255, 0), max(1, int(scale * 0.6)))
                    # White bounding box around ALL pixels in this cluster
                    _pixels = c_orig.get('pixels', [])
                    if _pixels:
                        _px_screen = [
                            (int((p[0]-x1)*scale), int((p[1]-y1)*scale))
                            for p in _pixels
                            if 0 <= int((p[0]-x1)*scale) < img.shape[1]
                            and 0 <= int((p[1]-y1)*scale) < img.shape[0]
                        ]
                        if _px_screen:
                            _bx1 = min(p[0] for p in _px_screen)
                            _by1 = min(p[1] for p in _px_screen)
                            _bx2 = max(p[0] for p in _px_screen)
                            _by2 = max(p[1] for p in _px_screen)
                            cv2.rectangle(img, (_bx1, _by1), (_bx2, _by2), (255, 255, 255), max(1, int(scale * 0.5)))
                    # Small label near centroid: "C cent" and near peak: "C peak"
                    _fs = max(0.3, 0.32 * scale)
                    cv2.putText(img, f"{_lbl_d}cent", (cx+int(3*scale), cy-int(5*scale)),
                                cv2.FONT_HERSHEY_PLAIN, _fs, (0, 255, 255), 1, cv2.LINE_AA)
                    cv2.putText(img, f"{_lbl_d}peak", (pcx+int(3*scale), pcy-int(5*scale)),
                                cv2.FONT_HERSHEY_PLAIN, _fs, (0, 0, 255), 1, cv2.LINE_AA)

                is_locked = locked_cluster is not None and c_orig is locked_cluster
                if is_locked:
                    cv2.circle(img, (pcx, pcy), int(20 * scale), (0, 0, 255), int(2 * scale))
                    cv2.drawMarker(img, (pcx, pcy), (0, 0, 255), cv2.MARKER_TILTED_CROSS, int(25 * scale), int(2 * scale))
                    
                    # Line-of-sight path from centroid to user (uses centroid for directional accuracy)
                    dist_to_user = math.hypot(ux - cx, uy - cy)
                    if dist_to_user > 10:
                        num_dots = int(dist_to_user / 8)
                        for d_idx in range(1, num_dots):
                            t = d_idx / num_dots
                            dot_x = int(cx + (ux - cx) * t)
                            dot_y = int(cy + (uy - cy) * t)
                            cv2.circle(img, (dot_x, dot_y), int(1 * scale), (0, 255, 0), -1)
                            
                    if (vx != 0.0 or vy != 0.0):
                        proj_pts = []
                        for step in range(1, 7):
                            px_proj = cx_orig + vx * step
                            py_proj = cy_orig + vy * step
                            c_proj_x = int((px_proj - x1) * scale)
                            c_proj_y = int((py_proj - y1) * scale)
                            proj_pts.append((c_proj_x, c_proj_y))
                        
                        for i in range(len(proj_pts)):
                            cv2.circle(img, proj_pts[i], int(2 * scale), (0, 0, 255), -1)
                            if i > 0:
                                cv2.line(img, proj_pts[i-1], proj_pts[i], (0, 0, 255), int(1 * scale))
                            else:
                                cv2.line(img, (cx, cy), proj_pts[0], (0, 0, 255), int(1 * scale))

                # Velocity arrow from centroid (direction/speed computation uses centroid)
                vx_s = int(vx * scale * 2.5)
                vy_s = int(vy * scale * 2.5)
                v_mag = math.hypot(vx_s, vy_s)
                if v_mag > 2:
                    cv2.arrowedLine(img, (cx, cy), (cx + vx_s, cy + vy_s), (200, 200, 200), max(1, int(scale * 0.8)), tipLength=0.3)
                    
                lbl = c_orig.get("label", "")
                if is_locked:
                    lbl = f"LOCKED[{locked_target_id}]"
                txt = f"{lbl}: {int(dbz)}"
                tw, th = int(55 * scale) if is_locked else int(45 * scale), int(12 * scale)
                # Label positioned above the PEAK marker (so text sits on the bright spot)
                tx = pcx - int(tw / 2)
                ty = pcy - int(16 * scale) - th
                
                labels.append({
                    'text': txt,
                    'type': 'ambient',
                    'margin': 0,
                    'w': tw, 'h': th,
                    'cx': tx + tw/2,
                    'cy': ty - th/2,
                    'ideal_cx': tx + tw/2,
                    'ideal_cy': ty - th/2,
                    'anchor_x': pcx,   # anchor line drawn to peak
                    'anchor_y': pcy,
                    'scale': 0.4 * scale,
                    'fg': (0, 0, 255) if is_locked else (200, 200, 200),
                    'bg': (255, 255, 255) if is_locked else (0, 0, 0)
                })

        # Draw the manual target lock marker at the exact locked coordinates if no cluster was matched
        if locked_target_id and locked_target_cx is not None and locked_target_cy is not None and locked_cluster is None:
            cx = int((locked_target_cx - x1) * scale)
            cy = int((locked_target_cy - y1) * scale)
            if 0 <= cx < img.shape[1] and 0 <= cy < img.shape[0]:
                cv2.circle(img, (cx, cy), int(20 * scale), (0, 0, 255), int(2 * scale))
                cv2.drawMarker(img, (cx, cy), (0, 0, 255), cv2.MARKER_TILTED_CROSS, int(25 * scale), int(2 * scale))
                
                txt = f"LOCKED[{locked_target_id}]"
                tw, th = int(65 * scale), int(15 * scale)
                tx = cx - int(tw / 2)
                ty = cy - int(20 * scale) - th
                labels.append({
                    'text': txt,
                    'type': 'approaching',
                    'margin': 8 * scale,
                    'w': tw, 'h': th,
                    'cx': tx + tw/2,
                    'cy': ty - th/2,
                    'ideal_cx': tx + tw/2,
                    'ideal_cy': ty - th/2,
                    'anchor_x': cx,
                    'anchor_y': cy,
                    'scale': 0.45 * scale,
                    'fg': (0, 0, 255),
                    'bg': (255, 255, 255)
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

        # Draw subtle 8x8 grid overlay for manual coordinate locking
        gh, gw = img.shape[0], img.shape[1]
        cell_w, cell_h = gw / 8, gh / 8
        grid_color = (80, 80, 80)
        grid_thickness = max(1, int(0.5 * scale))
        
        for c_idx in range(1, 8):
            x = int(c_idx * cell_w)
            cv2.line(img, (x, 0), (x, gh), grid_color, grid_thickness)
            
        for r_idx in range(1, 8):
            y = int(r_idx * cell_h)
            cv2.line(img, (0, y), (gw, y), grid_color, grid_thickness)
            
        font_scale = 0.4 * scale
        text_color = (200, 200, 200)
        bg_color = (0, 0, 0)
        
        for c_idx in range(8):
            label_x = chr(ord('A') + c_idx)
            tx = int((c_idx + 0.5) * cell_w - 6 * scale)
            cv2.putText(img, label_x, (tx, int(15 * scale)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, bg_color, max(1, int(font_scale * 4)))
            cv2.putText(img, label_x, (tx, int(15 * scale)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, max(1, int(font_scale * 1.5)))
            
        for r_idx in range(8):
            label_y = str(r_idx + 1)
            ty = int((r_idx + 0.5) * cell_h + 5 * scale)
            cv2.putText(img, label_y, (int(5 * scale), ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, bg_color, max(1, int(font_scale * 4)))
            cv2.putText(img, label_y, (int(5 * scale), ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, max(1, int(font_scale * 1.5)))

        from app.services.tmd_radar.processor import TMDRadarProcessor
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
    def render_rain_summary(predictions: list, confidence_cutoff_min: int = 90, time_offset_min: float = 0.0, confidence_score: float = 1.0, approaching_clouds: list = None, locked_target_id: str = None, all_rain_clusters: list = None, v_close_kmh: float = None, v_actual_kmh: float = None, v_avg_kmh: float = None) -> str:
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
            locked_cloud_detail_shown = False  # True once locked cloud ETA is written to text
            if locked_target_id:
                import re
                if re.match(r'^([a-hA-H])([1-8])$', locked_target_id):
                    target_desc = f"ช่องตาราง [{locked_target_id.upper()}]"
                elif re.match(r'^[a-zA-Z]{1,2}$', locked_target_id):
                    target_desc = f"กลุ่มฝน [{locked_target_id.upper()}]"
                else:
                    target_desc = "พิกัดแมนนวล"
                
                locked_cloud = None
                # Check all_rain_clusters (which contains all clouds) rather than just approaching_clouds (which only contains approaching ones)
                search_list = all_rain_clusters if all_rain_clusters else approaching_clouds
                if search_list:
                    for c in search_list:
                        if c.get("label") == locked_target_id:
                            locked_cloud = c
                            break
                if locked_cloud:
                    is_approaching = locked_cloud.get("approaching", False)
                    eta_val = locked_cloud.get("eta_min")
                    
                    speed_text = ""
                    if v_actual_kmh is not None and v_close_kmh is not None:
                        avg_str = f"\n- ความเร็วลมเฉลี่ยกลุ่มเมฆ: {v_avg_kmh:.1f} กม./ชม." if v_avg_kmh is not None else ""
                        speed_text = (
                            f"{avg_str}"
                            f"\n- ความเร็วลมสูงสุด: {v_actual_kmh:.1f} กม./ชม."
                            f"\n- ความเร็วลมสูงสุดที่โปรเจกต์บนเส้นสีเขียว: {v_close_kmh:.1f} กม./ชม."
                        )
                        
                    if eta_val is not None and eta_val < 9999.0 and v_close_kmh is not None and v_close_kmh > 0.05:
                        eta_val_adjusted = max(1.0, float(eta_val) - time_offset_min)
                        eta_h = int(eta_val_adjusted // 60)
                        eta_m = int(eta_val_adjusted % 60)
                        time_str = f"~{eta_h} ชม. {eta_m} นาที" if eta_h > 0 else f"~{eta_m} นาที"
                        if eta_h > 0 and eta_m == 0:
                            time_str = f"~{eta_h} ชม."
                        clock_time_str = fmt_clock_time(float(eta_val))
                        
                        if float(eta_val) > max_time:
                            context_str = "ซึ่งอยู่นอกช่วงเวลาพยากรณ์หลัก"
                        else:
                            context_str = "แต่คาดว่าแนวฝนจะเบี่ยงทิศทาง/สลายตัว หรือเคลื่อนผ่านใกล้เคียงโดยไม่ตกตรงตำแหน่งคุณ"
                            
                        text += f" (เนื่องจาก{target_desc} เคลื่อนที่เข้าหาตำแหน่งคุณ (ตามเส้นสีเขียว คาดว่าจะถึงในอีก {time_str} (เวลาประมาณ {clock_time_str})) {context_str}:{speed_text})"
                        locked_cloud_detail_shown = True  # ETA shown — suppress duplicate ☁️ note
                    else:
                        text += f" (เนื่องจาก{target_desc} มีแนวโน้มเคลื่อนที่ขนานหรือออกห่างจากตำแหน่งคุณ:{speed_text})"
                        locked_cloud_detail_shown = True  # cloud described — note would be redundant
                else:
                    text += f" (เนื่องจาก{target_desc} ไม่มีกลุ่มฝนในตำแหน่งล็อกหรือสลายตัวไปแล้ว)"
            if approaching_clouds:
                far_clouds = [c for c in approaching_clouds if c.get("eta_min", 0) > max_time]
                if locked_target_id:
                    far_clouds = [c for c in far_clouds if c.get("label") == locked_target_id]
                # Suppress the ☁️ note when the locked cloud was already fully described in the
                # main text above. The note uses eta_min from approaching_clouds
                # (find_approaching_clouds), while the main text uses eta_min from all_rain_clusters
                # (get_all_rain_clusters). These systems cluster pixels differently, so their ETAs
                # diverge — showing both creates a contradictory message.
                if far_clouds and not locked_cloud_detail_shown:
                    soonest = min(far_clouds, key=lambda c: c.get("eta_min", 999))
                    eta_val = max(1.0, float(soonest["eta_min"]) - time_offset_min)
                    eta_h = int(eta_val // 60)
                    eta_m = int(eta_val % 60)
                    time_str = f"~{eta_h} ชม. {eta_m} นาที" if eta_h > 0 else f"~{eta_m} นาที"
                    if eta_h > 0 and eta_m == 0:
                        time_str = f"~{eta_h} ชม."
                    soonest_lbl = soonest.get("label")
                    lbl_suffix = f"กลุ่มฝน [{soonest_lbl}] " if soonest_lbl else "กลุ่มฝน "
                    text += f"\n☁️ หมายเหตุ: ตรวจพบ{lbl_suffix}({int(soonest.get('dbz_now', 0))} dBZ) กำลังเคลื่อนมา อาจจะถึงในอีก {time_str} (เวลาประมาณ {fmt_clock_time(float(soonest['eta_min']))})"
            
            return text + warning

        start_idx = active_event["start_idx"]
        stop_idx = active_event["stop_idx"]
        max_dbz = active_event["max_dbz"]
        max_idx = active_event["max_idx"]
        
        start_time = predictions[start_idx]["time_offset"]
        start_dbz = predictions[start_idx]["dbz"]
        lbl_start = dbz_label(start_dbz)
        cluster_suffix = ""
        if locked_target_id:
            import re
            if re.match(r'^([a-hA-H])([1-8])$', locked_target_id):
                cluster_suffix = f" (ช่องตาราง [{locked_target_id.upper()}])"
            elif re.match(r'^[a-zA-Z]{1,2}$', locked_target_id):
                cluster_suffix = f" (กลุ่มฝน [{locked_target_id.upper()}])"
            else:
                cluster_suffix = " (พิกัดแมนนวล)"
        else:
            cluster_lbl = predictions[start_idx].get("cluster")
            cluster_suffix = f" (กลุ่มฝน [{cluster_lbl}])" if cluster_lbl else ""
        
        adj_start = start_time - time_offset_min
        
        if adj_start <= 0:
            msg_start = f"🌧️ ฝนกำลังตกอยู่ ({int(start_dbz)} dBZ — {lbl_start}){cluster_suffix}"
            if stop_idx == -1:
                max_time = predictions[-1]["time_offset"]
                msg_duration = f"และคาดว่าจะตกต่อเนื่องถึงอย่างน้อย {fmt_eta(max_time)} (เวลา {fmt_clock_time(max_time)})"
            else:
                stop_time = predictions[stop_idx]["time_offset"]
                msg_duration = f"และคาดว่าจะหยุดตกในอีก {fmt_eta(stop_time)} (เวลาประมาณ {fmt_clock_time(stop_time)})"
        else:
            msg_start = f"⏱ ฝนกำลังจะมาใน {fmt_eta(start_time)} (เวลาประมาณ {fmt_clock_time(start_time)}) ({int(start_dbz)} dBZ — {lbl_start}){cluster_suffix}"
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
