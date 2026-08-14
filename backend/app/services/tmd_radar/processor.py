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

from .clustering import TMDClusteringMixin
from .tracking import TMDTrackingMixin
from .multiframe import TMDMultiframeMixin
from .cache import TMDCacheMixin

class TMDRadarProcessor(TMDCacheMixin, TMDTrackingMixin, TMDMultiframeMixin, TMDClusteringMixin):
    def __init__(self, station_code: str, config: Optional["StationConfig"] = None):
        self.station_code = station_code
        if config:
            self.config = config
        else:
            from app.services.tmd_radar_registry import radar_registry
            if station_code in radar_registry._cached_stations:
                self.config = radar_registry._cached_stations[station_code]
            elif station_code in STATIONS:
                self.config = STATIONS[station_code]
            else:
                raise ValueError(f"Unknown station code: {station_code}")
        self.storage_dir = os.path.join(os.getcwd(), "backend", "tmp")

    def latlng_to_pixel(
        self,
        lat: float,
        lng: float,
        is_loop: bool = True,
        projection: str = None,
        frame_shape: Optional[Tuple[int, int]] = None,
    ) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box.

        Args:
            lat: Latitude of the point.
            lng: Longitude of the point.
            is_loop: Whether the frame is from the loop GIF (True) or static image (False).
            projection: Override the station's projection type ('linear' or 'azimuthal').
            frame_shape: Actual frame dimensions as (height, width). When supplied, the
                computed pixel coordinate is proportionally scaled from the config crop
                size to the real frame size. This is critical when Firestore-cached frames
                have been re-encoded at a different resolution than the original config
                (e.g., 800x800 cache vs 680x680 loop config).
        """
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

        # Derive config canvas size: total image size including crop offsets
        config_canvas_w = crop_x + crop_width
        config_canvas_h = crop_y + crop_height

        # Sentinel values — set by azimuthal branch, used by legacy-frame re-projection below
        pixel_radius: float = 0.0
        r_px: float = 0.0
        dx: float = 0.0
        dy: float = 0.0
        distance_km: float = 0.0

        if projection == "azimuthal" and hasattr(self.config, 'center_lat') and self.config.radius_km > 0:
            # Haversine distance
            R = 6371.0  # Earth radius in km
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
        else:
            # Fallback to standard linear interpolation using bounding box (Flat)
            x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
            y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)

            # Crop offsets
            px = int(x_pct * crop_width) + crop_x
            py = int(y_pct * crop_height) + crop_y

        # ── Scale to actual frame dimensions when they differ from config ──────
        # After Option 1 (crop-before-save), new frames are (crop_h × crop_w).
        # Legacy Firestore frames may still be full-image (e.g. 1920×1600).
        # In both cases we reconstruct the radar circle position in actual-frame
        # pixel space rather than blindly scaling px/py by a ratio.
        if frame_shape is not None:
            actual_h, actual_w = frame_shape[0], frame_shape[1]
            crop_is_frame = (
                abs(actual_h - crop_height) <= 4 and abs(actual_w - crop_width) <= 4
            )
            if crop_is_frame:
                # ── New (cropped) frame: px/py are already in crop coords ──────
                # latlng_to_pixel computed px relative to crop_x/crop_y offsets,
                # so we need to remove those offsets when the frame IS the crop.
                px = px - crop_x
                py = py - crop_y
                logger.debug(
                    f"latlng_to_pixel: cropped frame ({actual_w}x{actual_h}) — "
                    f"removed crop offset → ({px},{py})"
                )
            else:
                # ── Legacy (full) frame: re-project onto actual image space ───
                # The config defines where the radar circle sits in the original
                # full-image canvas.  Scale that geometry to the actual frame.
                scale_x = actual_w / config_canvas_w
                scale_y = actual_h / config_canvas_h

                # Radar circle center in full-image coords, then scaled
                radar_cx_full = crop_x + crop_width / 2.0
                radar_cy_full = crop_y + crop_height / 2.0
                real_center_x = radar_cx_full * scale_x
                real_center_y = radar_cy_full * scale_y
                # Radius scales with the x-axis (circles keep aspect ratio)
                real_radius_px = (crop_width / 2.0) * scale_x

                # Re-derive bearing vectors from the already-computed dx/dy
                # which are normalised to pixel_radius (= crop_width/2).
                # dx = r_px * sin(bearing), dy = -r_px * cos(bearing)
                # → sin_b = dx/r_px, cos_b = -dy/r_px  (when r_px > 0)
                if pixel_radius > 0 and r_px > 0:
                    sin_b = dx / pixel_radius
                    cos_b = -dy / pixel_radius
                    r_real = (distance_km / self.config.radius_km) * real_radius_px
                    px = int(round(real_center_x + r_real * sin_b))
                    py = int(round(real_center_y - r_real * cos_b))
                else:
                    px = int(round(real_center_x))
                    py = int(round(real_center_y))

                logger.debug(
                    f"latlng_to_pixel: full-image frame ({actual_w}x{actual_h}) — "
                    f"re-projected → ({px},{py}) "
                    f"[circle_center=({real_center_x:.0f},{real_center_y:.0f}), "
                    f"r={real_radius_px:.0f}px, scale=({scale_x:.3f},{scale_y:.3f})]"
                )

        return px, py
