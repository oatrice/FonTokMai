#!/usr/bin/env python3
"""
radar_bot.py — Standalone Telegram Weather Radar Edge Detection Bot
====================================================================
TMD Sakon Nakhon Radar (SKN-240) — Storm Cloud Boundary Detection

ต้องการ environment variables:
  TELEGRAM_BOT_TOKEN=<your token>
  RADAR_URL=https://weather.tmd.go.th/skn/sknloop.gif  (optional override)

รัน:
  python radar_bot.py

Dry-run test (บันทึก test_output.png ไม่ต้อง token):
  python radar_bot.py --test [x] [y]
"""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageSequence

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("radar_bot")

# ──────────────────────────────────────────────────────────────
# 1.  CONSTANTS & DBZ SCALE
# ──────────────────────────────────────────────────────────────

DEFAULT_RADAR_URL = os.getenv(
    "RADAR_URL", "https://weather.tmd.go.th/skn/sknloop.gif"
)

# SKN-240 geographic bounding box (from tmd_radar_config.py)
SKN_LAT_MAX = 19.32
SKN_LAT_MIN = 15.00
SKN_LON_MIN = 101.95
SKN_LON_MAX = 106.35

IMG_W = 800
IMG_H = 800
CROP_R = 120
SCALE = 3.0
CANVAS_SIZE = int(CROP_R * 2 * SCALE)  # 720
PIN_CX = CANVAS_SIZE // 2  # 360
PIN_CY = CANVAS_SIZE // 2  # 360
PX_PER_KM = 4.37
DEFAULT_USER_X = 486
DEFAULT_USER_Y = 390
MIN_PERIMETER = 25
DBZ_COLOR_THRESH = 75
_SATURATION_MIN = 30

DBZ_SCALE: List[dict] = [
    {"dbz": 10.5, "rgb": (  0,  70,   0), "label": "ฝนตกเบาบางมาก"},
    {"dbz": 11.5, "rgb": (  0, 100,   0), "label": "ฝนตกเบาบาง"},
    {"dbz": 16.5, "rgb": (  0, 140,   0), "label": "ฝนละอองเบา"},
    {"dbz": 19.0, "rgb": (  0, 180,   0), "label": "ฝนเบาพัดผ่าน"},
    {"dbz": 21.5, "rgb": (  0, 220,   0), "label": "ฝนเบาต่อเนื่อง"},
    {"dbz": 24.0, "rgb": (  0, 255,   0), "label": "ฝนตกทั่วไป"},
    {"dbz": 26.5, "rgb": ( 50, 255,   0), "label": "ฝนกำลังตกอ่อน"},
    {"dbz": 29.0, "rgb": (120, 255,   0), "label": "ฝนอ่อนถึงปานกลาง"},
    {"dbz": 31.5, "rgb": (190, 255,   0), "label": "ฝนปานกลางพัดผ่าน"},
    {"dbz": 34.0, "rgb": (255, 255,   0), "label": "ฝนปานกลางทั่วไป"},
    {"dbz": 36.5, "rgb": (255, 220,   0), "label": "ฝนหนักสะสม"},
    {"dbz": 39.0, "rgb": (255, 190,   0), "label": "ฝนหนักเป็นหย่อม"},
    {"dbz": 41.5, "rgb": (255, 160,   0), "label": "ฝนหนักต่อเนื่อง"},
    {"dbz": 44.0, "rgb": (255, 120,   0), "label": "ฝนหนักรุนแรงพัดผ่าน"},
    {"dbz": 46.5, "rgb": (255,  80,   0), "label": "ฝนตกหนักรุนแรงมาก"},
    {"dbz": 49.0, "rgb": (255,  40,  40), "label": "พายุฝนฟ้าคะนอง"},
    {"dbz": 51.5, "rgb": (255,   0,   0), "label": "พายุฝนรุนแรงจัด"},
    {"dbz": 54.0, "rgb": (204,   0,   0), "label": "พายุฝนฟ้าคะนองรุนแรง"},
    {"dbz": 56.5, "rgb": (200,   0, 255), "label": "พายุหมุนรุนแรงมาก"},
    {"dbz": 59.0, "rgb": (255,   0, 255), "label": "พายุลูกเห็บ/ทอร์นาโดต้น"},
    {"dbz": 61.5, "rgb": (255, 120, 255), "label": "พายุทำลายล้างเฉียบพลัน"},
    {"dbz": 64.0, "rgb": (255, 190, 255), "label": "พายุลูกเห็บเม็ดใหญ่จัด"},
    {"dbz": 66.5, "rgb": (255, 230, 255), "label": "จุดวิกฤตพายุทำลายล้างสูงสุด"},
]


# ──────────────────────────────────────────────────────────────
# 2.  DATA CLASSES
# ──────────────────────────────────────────────────────────────

@dataclass
class StormContour:
    points: np.ndarray
    max_dbz: float
    label: str
    fill_color_rgba: Tuple
    stroke_color_rgb: Tuple
    area_px: float


@dataclass
class RadarResult:
    contours: List[StormContour]
    user_inside: bool
    nearest_km: Optional[float]
    max_dbz_in_area: float
    peak_label: str
    canvas_bgr: np.ndarray
    radar_time_label: str
    fetch_ok: bool


# ──────────────────────────────────────────────────────────────
# 3.  RADAR PROCESSOR
# ──────────────────────────────────────────────────────────────

class RadarProcessor:

    def __init__(self, radar_url: str = DEFAULT_RADAR_URL, timeout: float = 15.0):
        self.radar_url = radar_url
        self.timeout = timeout
        self._raw_rgb: Optional[np.ndarray] = None
        self._fetch_ts: float = 0.0

    async def fetch_radar_frame(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(self.radar_url)
                resp.raise_for_status()
                data = resp.content

            pil_img = Image.open(io.BytesIO(data))
            last_frame: Optional[Image.Image] = None
            try:
                frames = list(ImageSequence.Iterator(pil_img))
                last_frame = frames[-1].convert("RGB")
            except Exception:
                last_frame = pil_img.convert("RGB")

            arr = np.array(last_frame, dtype=np.uint8)
            if arr.shape[0] != IMG_H or arr.shape[1] != IMG_W:
                arr = cv2.resize(arr, (IMG_W, IMG_H), interpolation=cv2.INTER_LANCZOS4)

            self._raw_rgb = arr
            self._fetch_ts = time.time()
            logger.info(f"Fetched radar frame {arr.shape}")
            return True

        except Exception as exc:
            logger.error(f"fetch_radar_frame failed: {exc}")
            return False

    @staticmethod
    def _is_storm_pixel(r: int, g: int, b: int) -> Tuple[bool, float, str]:
        sat = max(r, g, b) - min(r, g, b)
        if sat < _SATURATION_MIN:
            return False, 0.0, ""

        best_dist = float("inf")
        best_dbz = 0.0
        best_label = ""

        for entry in DBZ_SCALE:
            er, eg, eb = entry["rgb"]
            dist = math.sqrt((r - er) ** 2 + (g - eg) ** 2 + (b - eb) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_dbz = entry["dbz"]
                best_label = entry["label"]

        if best_dist > DBZ_COLOR_THRESH:
            return False, 0.0, ""
        if best_dbz < 11.5:
            return False, 0.0, ""
        return True, best_dbz, best_label

    @staticmethod
    def _dbz_to_fill_rgba(dbz: float) -> Tuple[int, int, int, int]:
        if dbz >= 56.5:   return (200,   0, 255, 110)
        elif dbz >= 49.0: return (255,   0,   0, 110)
        elif dbz >= 44.0: return (255, 100,   0, 105)
        elif dbz >= 36.5: return (255, 200,   0, 100)
        elif dbz >= 29.0: return (130, 255,   0,  90)
        elif dbz >= 21.5: return (  0, 200,   0,  80)
        else:             return (  0, 120,   0,  70)

    @staticmethod
    def _dbz_to_stroke_rgb(dbz: float) -> Tuple[int, int, int]:
        if dbz >= 56.5:   return (220,  80, 255)
        elif dbz >= 49.0: return (255,  80,  80)
        elif dbz >= 44.0: return (255, 160,   0)
        elif dbz >= 36.5: return (255, 240,   0)
        elif dbz >= 29.0: return (160, 255,   0)
        elif dbz >= 21.5: return (  0, 255, 100)
        else:             return (  0, 200,  50)

    def _build_storm_mask(
        self, rgb_frame: np.ndarray, x1: int, y1: int, x2: int, y2: int
    ) -> Tuple[np.ndarray, np.ndarray, float, str]:
        crop = rgb_frame[y1:y2, x1:x2].copy()
        h, w = crop.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        max_dbz = 0.0
        peak_label = "ไม่มีฝนในพื้นที่"

        for py in range(h):
            for px in range(w):
                r, g, b = int(crop[py, px, 0]), int(crop[py, px, 1]), int(crop[py, px, 2])
                is_storm, dbz, lbl = self._is_storm_pixel(r, g, b)
                if is_storm:
                    mask[py, px] = 255
                    if dbz > max_dbz:
                        max_dbz = dbz
                        peak_label = lbl

        return crop, mask, max_dbz, peak_label

    @staticmethod
    def _chaikin_smooth(points: np.ndarray, iterations: int = 3) -> np.ndarray:
        """Chaikin Corner-Cutting: Q=0.75P+0.25P+1, R=0.25P+0.75P+1"""
        pts = points.astype(np.float32)
        for _ in range(iterations):
            n = len(pts)
            new_pts = np.empty((n * 2, 2), dtype=np.float32)
            for i in range(n):
                p0 = pts[i]
                p1 = pts[(i + 1) % n]
                new_pts[2 * i]     = 0.75 * p0 + 0.25 * p1  # Q
                new_pts[2 * i + 1] = 0.25 * p0 + 0.75 * p1  # R
            pts = new_pts
        return pts

    def _extract_smooth_contours(
        self,
        crop_rgb: np.ndarray,
        mask_raw: np.ndarray,
        max_dbz: float,
        peak_label: str,
    ) -> List[StormContour]:
        mask_up = cv2.resize(mask_raw, (CANVAS_SIZE, CANVAS_SIZE), interpolation=cv2.INTER_LANCZOS4)
        _, mask_up = cv2.threshold(mask_up, 127, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_up = cv2.morphologyEx(mask_up, cv2.MORPH_CLOSE, kernel)

        contours_raw, _ = cv2.findContours(mask_up, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        result: List[StormContour] = []
        for ctr in contours_raw:
            perim = cv2.arcLength(ctr, closed=True)
            if perim < MIN_PERIMETER:
                continue

            area = cv2.contourArea(ctr)
            pts = ctr.squeeze(axis=1).astype(np.float32)
            if pts.ndim != 2 or len(pts) < 3:
                continue

            smooth_pts = self._chaikin_smooth(pts, iterations=3)

            M = cv2.moments(ctr)
            if M["m00"] > 0:
                sample_x = int(M["m10"] / M["m00"])
                sample_y = int(M["m01"] / M["m00"])
            else:
                sample_x, sample_y = int(pts[0, 0]), int(pts[0, 1])

            crop_h, crop_w = mask_raw.shape[:2]
            crop_sx = max(0, min(int(sample_x / CANVAS_SIZE * crop_w), crop_w - 1))
            crop_sy = max(0, min(int(sample_y / CANVAS_SIZE * crop_h), crop_h - 1))

            r = int(crop_rgb[crop_sy, crop_sx, 0])
            g = int(crop_rgb[crop_sy, crop_sx, 1])
            b = int(crop_rgb[crop_sy, crop_sx, 2])
            _, dbz, lbl = self._is_storm_pixel(r, g, b)
            if dbz == 0.0:
                dbz = 11.5
                lbl = "ฝนตกเบาบาง"

            result.append(
                StormContour(
                    points=smooth_pts,
                    max_dbz=dbz,
                    label=lbl,
                    fill_color_rgba=self._dbz_to_fill_rgba(dbz),
                    stroke_color_rgb=self._dbz_to_stroke_rgb(dbz),
                    area_px=area,
                )
            )

        result.sort(key=lambda c: c.max_dbz, reverse=True)
        return result

    @staticmethod
    def _proximity_test(
        contours: List[StormContour],
        cx: int = PIN_CX,
        cy: int = PIN_CY,
    ) -> Tuple[bool, Optional[float]]:
        user_inside = False
        min_dist_px = float("inf")

        for sc in contours:
            pts_int = sc.points.astype(np.int32).reshape(-1, 1, 2)
            test = cv2.pointPolygonTest(pts_int, (float(cx), float(cy)), measureDist=True)
            if test >= 0:
                user_inside = True
                break
            dist = abs(test)
            if dist < min_dist_px:
                min_dist_px = dist

        if user_inside:
            return True, None
        if min_dist_px == float("inf"):
            return False, None
        return False, min_dist_px / PX_PER_KM

    async def process(
        self,
        user_x: int = DEFAULT_USER_X,
        user_y: int = DEFAULT_USER_Y,
    ) -> RadarResult:
        fetch_ok = await self.fetch_radar_frame()

        if not fetch_ok or self._raw_rgb is None:
            return RadarResult(
                contours=[],
                user_inside=False,
                nearest_km=None,
                max_dbz_in_area=0.0,
                peak_label="ไม่สามารถดึงข้อมูล Radar ได้",
                canvas_bgr=np.zeros((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.uint8),
                radar_time_label="N/A",
                fetch_ok=False,
            )

        rgb = self._raw_rgb
        x1 = max(0, user_x - CROP_R)
        y1 = max(0, user_y - CROP_R)
        x2 = min(IMG_W, user_x + CROP_R)
        y2 = min(IMG_H, user_y + CROP_R)

        crop_rgb, mask_raw, max_dbz, peak_label = self._build_storm_mask(rgb, x1, y1, x2, y2)

        canvas_bgr = cv2.resize(
            cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2BGR),
            (CANVAS_SIZE, CANVAS_SIZE),
            interpolation=cv2.INTER_LANCZOS4,
        )

        contours = self._extract_smooth_contours(crop_rgb, mask_raw, max_dbz, peak_label)
        user_inside, nearest_km = self._proximity_test(contours)

        from datetime import datetime, timezone, timedelta
        thai_tz = timezone(timedelta(hours=7))
        now_thai = datetime.now(thai_tz)
        time_label = f"ล่าสุด {now_thai.strftime('%H:%M')} น. ({now_thai.strftime('%d/%m/%Y')})"

        return RadarResult(
            contours=contours,
            user_inside=user_inside,
            nearest_km=nearest_km,
            max_dbz_in_area=max_dbz,
            peak_label=peak_label,
            canvas_bgr=canvas_bgr,
            radar_time_label=time_label,
            fetch_ok=True,
        )


# ──────────────────────────────────────────────────────────────
# 4.  IMAGE RENDERER
# ──────────────────────────────────────────────────────────────

class ImageRenderer:

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            "/System/Library/Fonts/Supplemental/Thonburi.ttc",
            "/System/Library/Fonts/ThonburiUI.ttc",
            "/System/Library/Fonts/Supplemental/Ayuthaya.ttf",
            "/System/Library/Fonts/Supplemental/Sathu.ttf",
            "/System/Library/Fonts/Supplemental/Tahoma.ttf",
            "/Library/Fonts/Tahoma.ttf",
            "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
            "/usr/share/fonts/truetype/tlwg/Loma.ttf",
            "/usr/share/fonts/truetype/thai-tlwg/Garuda.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
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

    @staticmethod
    def _draw_neon_polyline(
        canvas: Image.Image,
        pts: np.ndarray,
        stroke_rgb: Tuple[int, int, int],
        closed: bool = True,
    ) -> None:
        """Multi-pass neon glow: wide blurred layers + sharp centerline."""
        xy = [(float(p[0]), float(p[1])) for p in pts]
        if closed and len(xy) > 2:
            xy.append(xy[0])

        layers = [
            (12, 8, 55),
            (6,  4, 110),
            (3,  2, 180),
            (2,  0, 255),
        ]
        r, g, b = stroke_rgb

        for lw, blur_r, alpha in layers:
            layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.line(xy, fill=(r, g, b, alpha), width=lw)
            if blur_r > 0:
                layer = layer.filter(ImageFilter.GaussianBlur(radius=blur_r))
            canvas.alpha_composite(layer)

    @staticmethod
    def _draw_fill(
        canvas: Image.Image,
        pts: np.ndarray,
        fill_rgba: Tuple[int, int, int, int],
    ) -> None:
        xy = [(float(p[0]), float(p[1])) for p in pts]
        if len(xy) < 3:
            return
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.polygon(xy, fill=fill_rgba)
        canvas.alpha_composite(layer)

    @staticmethod
    def _draw_user_pin(canvas: Image.Image, cx: int = PIN_CX, cy: int = PIN_CY) -> None:
        d = ImageDraw.Draw(canvas)
        # Pulse rings
        d.ellipse([(cx - 24, cy - 24), (cx + 24, cy + 24)], outline=(0, 220, 255, 140), width=2)
        d.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], outline=(255, 255, 255, 200), width=2)
        # Crosshair
        arm = 20
        d.line([(cx - arm, cy), (cx + arm, cy)], fill=(255, 255, 255, 255), width=2)
        d.line([(cx, cy - arm), (cx, cy + arm)], fill=(255, 255, 255, 255), width=2)
        # Centre dot (cyan)
        d.ellipse([(cx - 4, cy - 4), (cx + 4, cy + 4)], fill=(0, 255, 180, 255))

    @staticmethod
    def _draw_compass(canvas: Image.Image, font: ImageFont.FreeTypeFont) -> None:
        d = ImageDraw.Draw(canvas)
        ox, oy = CANVAS_SIZE - 50, CANVAS_SIZE - 50
        arm = 22
        # N (white triangle pointing up)
        d.polygon([(ox, oy - arm), (ox - 7, oy + 5), (ox + 7, oy + 5)],
                  fill=(255, 255, 255, 210))
        # S (dark grey)
        d.polygon([(ox, oy + arm), (ox - 6, oy - 4), (ox + 6, oy - 4)],
                  fill=(140, 140, 140, 190))
        # E/W axis
        d.line([(ox - arm, oy), (ox + arm, oy)], fill=(200, 200, 200, 180), width=2)
        fn = ImageRenderer._load_font(10)
        d.text((ox - 4, oy - arm - 15), "N", fill=(255, 255, 255), font=fn)
        d.text((ox - 4, oy + arm + 3),  "S", fill=(180, 180, 180), font=fn)
        d.text((ox + arm + 3, oy - 6),  "E", fill=(180, 180, 180), font=fn)
        d.text((ox - arm - 14, oy - 6), "W", fill=(180, 180, 180), font=fn)

    @staticmethod
    def _draw_scale_bar(canvas: Image.Image, font: ImageFont.FreeTypeFont) -> None:
        d = ImageDraw.Draw(canvas)
        bar_px = int(10 * PX_PER_KM)
        bx, by = 20, CANVAS_SIZE - 30
        # Shadow
        d.rectangle([(bx, by + 1), (bx + bar_px, by + 8)], fill=(0, 0, 0, 150))
        d.rectangle([(bx, by), (bx + bar_px, by + 7)], fill=(255, 255, 255, 210))
        # Tick marks at ends and centre
        for tx in [bx, bx + bar_px // 2, bx + bar_px]:
            d.line([(tx, by - 3), (tx, by)], fill=(255, 255, 255), width=2)
        d.text((bx, by + 10), "0", fill=(220, 220, 220), font=font)
        d.text((bx + bar_px // 2 - 8, by + 10), "5km", fill=(220, 220, 220), font=font)
        d.text((bx + bar_px + 2, by + 10), "10km", fill=(220, 220, 220), font=font)

    @staticmethod
    def _draw_banner(
        canvas: Image.Image,
        result: RadarResult,
        font: ImageFont.FreeTypeFont,
        font_sm: ImageFont.FreeTypeFont,
    ) -> None:
        d = ImageDraw.Draw(canvas)
        d.rectangle([(0, 0), (CANVAS_SIZE, 58)], fill=(0, 0, 0, 175))

        # Time + source
        d.text((10, 5), f"SKN-240  {result.radar_time_label}", fill=(140, 200, 255), font=font_sm)

        if not result.fetch_ok:
            status = "⚠ ดึงข้อมูล Radar ไม่ได้"
            color = (255, 90, 90)
        elif result.user_inside:
            status = f"📍 อยู่ในพื้นที่ฝน — {result.peak_label}"
            color = (255, 80, 80)
        elif result.nearest_km is not None:
            status = f"🌧 ฝนใกล้สุด {result.nearest_km:.1f} กม. — {result.peak_label}"
            color = (255, 230, 60)
        elif result.max_dbz_in_area == 0.0:
            status = "✅ ท้องฟ้าปลอดโปร่ง ไม่มีฝนในรัศมี"
            color = (80, 255, 140)
        else:
            status = f"🌂 {result.peak_label}"
            color = (180, 255, 100)

        d.text((10, 30), status, fill=color, font=font)

        # dBZ badge (top-right)
        if result.max_dbz_in_area > 0:
            badge_text = f"{result.max_dbz_in_area:.0f} dBZ"
            d.text((CANVAS_SIZE - 80, 18), badge_text, fill=(255, 220, 100), font=font)

    @staticmethod
    def _draw_legend(canvas: Image.Image, font_sm: ImageFont.FreeTypeFont) -> None:
        """Compact legend (top-right, below banner)."""
        d = ImageDraw.Draw(canvas)
        visible = [e for e in DBZ_SCALE if e["dbz"] >= 21.5]  # skip lowest 2 for space
        lx = CANVAS_SIZE - 128
        ly = 65
        lw = 123
        lh = len(visible) * 14 + 8
        d.rectangle([(lx - 3, ly - 3), (lx + lw, ly + lh)], fill=(0, 0, 0, 165))
        d.text((lx, ly - 2), "dBZ", fill=(180, 180, 180), font=font_sm)
        for i, entry in enumerate(reversed(visible)):
            r, g, b = entry["rgb"]
            ey = ly + 14 + i * 14
            d.rectangle([(lx, ey), (lx + 12, ey + 10)], fill=(r, g, b))
            d.text((lx + 16, ey - 1),
                   f"{entry['dbz']:.0f} {entry['label'][:8]}",
                   fill=(210, 210, 210), font=font_sm)

    def render(self, result: RadarResult) -> bytes:
        base_rgb = cv2.cvtColor(result.canvas_bgr, cv2.COLOR_BGR2RGB)
        canvas = Image.fromarray(base_rgb, "RGB").convert("RGBA")

        font = self._load_font(15)
        font_sm = self._load_font(11)

        # Fills first (behind contour lines)
        for sc in result.contours:
            self._draw_fill(canvas, sc.points, sc.fill_color_rgba)

        # Neon contour lines
        for sc in result.contours:
            self._draw_neon_polyline(canvas, sc.points, sc.stroke_color_rgb)

        # User pin on top
        self._draw_user_pin(canvas)

        # UI overlays
        self._draw_banner(canvas, result, font, font_sm)
        self._draw_scale_bar(canvas, font_sm)
        self._draw_compass(canvas, font_sm)
        self._draw_legend(canvas, font_sm)

        buf = io.BytesIO()
        canvas.convert("RGB").save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf.read()


# ──────────────────────────────────────────────────────────────
# 5.  REPORT BUILDER
# ──────────────────────────────────────────────────────────────

class ReportBuilder:

    @staticmethod
    def _severity_emoji(dbz: float) -> str:
        if dbz >= 56.5:   return "🌀"
        elif dbz >= 49.0: return "⛈️"
        elif dbz >= 44.0: return "🌩️"
        elif dbz >= 36.5: return "🌧️"
        elif dbz >= 29.0: return "🌦️"
        elif dbz >= 21.5: return "🌂"
        else:             return "🌫️"

    @staticmethod
    def build(result: RadarResult, user_x: int, user_y: int) -> str:
        if not result.fetch_ok:
            return (
                "⚠️ *ไม่สามารถดึงข้อมูล Radar ได้*\n"
                "กรุณาลองใหม่อีกครั้งในภายหลัง"
            )

        lines: List[str] = [
            "🛰️ *รายงานสภาพอากาศ — Radar SKN-240*",
            f"🕐 {result.radar_time_label}",
            f"📍 พิกัด: X={user_x}, Y={user_y}",
            "",
        ]

        if result.max_dbz_in_area == 0.0:
            lines.append("✅ *ท้องฟ้าปลอดโปร่ง ไม่พบฝนในรัศมี 120 กม.*")
        else:
            emoji = ReportBuilder._severity_emoji(result.max_dbz_in_area)
            lines += [
                f"{emoji} *สภาพฝน:* {result.peak_label}",
                f"📊 ความแรงสูงสุด: *{result.max_dbz_in_area:.1f} dBZ*",
                "",
            ]
            if result.user_inside:
                lines += [
                    "🔴 *คุณอยู่ในพื้นที่ฝนตกขณะนี้!*",
                    "   ⚠️ แนะนำหลบหรือกางร่มทันที",
                ]
            elif result.nearest_km is not None:
                km = result.nearest_km
                lines.append(f"📏 ฝนอยู่ห่าง *{km:.1f} กม.*")
                if km < 5:
                    lines.append("   🔶 ระวัง! ฝนกำลังเข้าใกล้มาก")
                elif km < 15:
                    lines.append("   🟡 ฝนอยู่ในระยะใกล้ ควรระวัง")
                elif km < 30:
                    lines.append("   🟢 ฝนอยู่ในรัศมีปานกลาง")
                else:
                    lines.append("   🔵 ฝนอยู่ห่างไกล ติดตามต่อเนื่อง")
            else:
                lines.append("ℹ️ ตรวจพบพื้นที่ฝนในรัศมีการสแกน")

            lines += [
                "",
                f"🔢 *พบขอบเขตพายุ:* {len(result.contours)} กลุ่ม",
            ]

        lines += [
            "",
            "─────────────────────",
            "💡 ข้อมูลจาก TMD Radar SKN-240",
            "📡 อัปเดตทุก ~6 นาที | /help สำหรับคำสั่งทั้งหมด",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# 6.  GPS → PIXEL MAPPER
# ──────────────────────────────────────────────────────────────

def gps_to_pixel(lat: float, lon: float) -> Tuple[int, int]:
    """Map GPS coordinates to 800×800 SKN-240 pixel coordinates."""
    px = int((lon - SKN_LON_MIN) / (SKN_LON_MAX - SKN_LON_MIN) * IMG_W)
    py = int((SKN_LAT_MAX - lat) / (SKN_LAT_MAX - SKN_LAT_MIN) * IMG_H)
    return max(0, min(px, IMG_W - 1)), max(0, min(py, IMG_H - 1))


# ──────────────────────────────────────────────────────────────
# 7.  PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────────────────────

async def run_radar_pipeline(user_x: int, user_y: int) -> Tuple[bytes, str]:
    processor = RadarProcessor()
    result = await processor.process(user_x, user_y)
    renderer = ImageRenderer()
    image_bytes = renderer.render(result)
    report = ReportBuilder.build(result, user_x, user_y)
    return image_bytes, report


# ──────────────────────────────────────────────────────────────
# 8.  TELEGRAM BOT HANDLERS
# ──────────────────────────────────────────────────────────────

HELP_TEXT = """
🛰️ *บอทตรวจจับขอบพายุ Radar SKN-240*

ยินดีต้อนรับ! บอทนี้วิเคราะห์ภาพ Radar ล่าสุดจาก TMD สถานีสกลนคร
ตรวจจับขอบเขตพายุด้วย Computer Vision แล้วส่งภาพพร้อมรายงานกลับมา

*📡 คำสั่งที่ใช้ได้:*

`/track X Y` — วิเคราะห์พิกัด pixel บนภาพ 800×800
  ตัวอย่าง: `/track 486 390`

`/gps lat lon` — ระบุพิกัด GPS
  ตัวอย่าง: `/gps 17.16 104.14`
  ครอบคลุม: lat 15.00–19.32, lon 101.95–106.35

📍 *ส่งพิกัดสถานที่* — กด 📎 → Location
  บอทวิเคราะห์พิกัดให้อัตโนมัติ

*⚙️ เทคนิค:*
• dBZ Segmentation 23 ระดับ (10.5–66.5 dBZ)
• Chaikin Corner-Cutting Smoothing (3 รอบ)
• OpenCV findContours + pointPolygonTest
• Neon Glow Rendering (PIL multi-pass)
• Scale: 1 กม. ≈ 4.37 px บน canvas 720×720
""".strip()


def build_telegram_app():
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

    async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ รูปแบบไม่ถูกต้อง\nใช้: `/track X Y`\nเช่น: `/track 486 390`",
                parse_mode="Markdown",
            )
            return
        try:
            user_x, user_y = int(args[0]), int(args[1])
        except ValueError:
            await update.message.reply_text("⚠️ X และ Y ต้องเป็นตัวเลขจำนวนเต็ม")
            return
        if not (0 <= user_x < IMG_W and 0 <= user_y < IMG_H):
            await update.message.reply_text(
                f"⚠️ พิกัดต้องอยู่ในช่วง 0–{IMG_W-1} (X) และ 0–{IMG_H-1} (Y)"
            )
            return

        loading = await update.message.reply_text("⏳ กำลังวิเคราะห์ภาพ Radar...")
        try:
            image_bytes, report = await run_radar_pipeline(user_x, user_y)
            await loading.delete()
            await update.message.reply_photo(
                photo=io.BytesIO(image_bytes),
                caption=report,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.exception("cmd_track error")
            await loading.edit_text(f"❌ เกิดข้อผิดพลาด: {exc}")

    async def cmd_gps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "⚠️ รูปแบบไม่ถูกต้อง\nใช้: `/gps lat lon`\nเช่น: `/gps 17.16 104.14`",
                parse_mode="Markdown",
            )
            return
        try:
            lat, lon = float(args[0]), float(args[1])
        except ValueError:
            await update.message.reply_text("⚠️ ต้องเป็นตัวเลขทศนิยม")
            return

        if not (SKN_LAT_MIN <= lat <= SKN_LAT_MAX):
            await update.message.reply_text(
                f"⚠️ Latitude ต้องอยู่ระหว่าง {SKN_LAT_MIN}–{SKN_LAT_MAX}"
            )
            return
        if not (SKN_LON_MIN <= lon <= SKN_LON_MAX):
            await update.message.reply_text(
                f"⚠️ Longitude ต้องอยู่ระหว่าง {SKN_LON_MIN}–{SKN_LON_MAX}"
            )
            return

        user_x, user_y = gps_to_pixel(lat, lon)
        loading = await update.message.reply_text(
            f"📌 GPS ({lat:.4f}°N, {lon:.4f}°E) → Pixel ({user_x}, {user_y})\n⏳ กำลังวิเคราะห์..."
        )
        try:
            image_bytes, report = await run_radar_pipeline(user_x, user_y)
            gps_suffix = f"\n\n📌 GPS: {lat:.4f}°N, {lon:.4f}°E → Pixel ({user_x}, {user_y})"
            await loading.delete()
            await update.message.reply_photo(
                photo=io.BytesIO(image_bytes),
                caption=report + gps_suffix,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.exception("cmd_gps error")
            await loading.edit_text(f"❌ เกิดข้อผิดพลาด: {exc}")

    async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        loc = update.message.location
        lat, lon = loc.latitude, loc.longitude

        if not (SKN_LAT_MIN <= lat <= SKN_LAT_MAX and SKN_LON_MIN <= lon <= SKN_LON_MAX):
            await update.message.reply_text(
                f"⚠️ พิกัดของคุณ ({lat:.4f}°N, {lon:.4f}°E) "
                f"อยู่นอกพื้นที่ครอบคลุมของ Radar SKN-240\n"
                f"รองรับ: Lat {SKN_LAT_MIN}–{SKN_LAT_MAX}, Lon {SKN_LON_MIN}–{SKN_LON_MAX}"
            )
            return

        user_x, user_y = gps_to_pixel(lat, lon)
        loading = await update.message.reply_text(
            f"📍 รับพิกัดแล้ว: {lat:.4f}°N, {lon:.4f}°E\n⏳ กำลังวิเคราะห์..."
        )
        try:
            image_bytes, report = await run_radar_pipeline(user_x, user_y)
            gps_suffix = f"\n\n📌 GPS: {lat:.4f}°N, {lon:.4f}°E → Pixel ({user_x}, {user_y})"
            await loading.delete()
            await update.message.reply_photo(
                photo=io.BytesIO(image_bytes),
                caption=report + gps_suffix,
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.exception("handle_location error")
            await loading.edit_text(f"❌ เกิดข้อผิดพลาด: {exc}")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("track", cmd_track))
    app.add_handler(CommandHandler("gps",   cmd_gps))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    return app


# ──────────────────────────────────────────────────────────────
# 9.  DRY-RUN TEST
# ──────────────────────────────────────────────────────────────

async def _dry_run_test(user_x: int, user_y: int) -> None:
    print(f"[DRY-RUN] Processing pixel ({user_x}, {user_y}) ...")
    image_bytes, report = await run_radar_pipeline(user_x, user_y)
    out_path = "test_radar_output.png"
    with open(out_path, "wb") as f:
        f.write(image_bytes)
    print(f"[DRY-RUN] ✅ Image saved → {out_path}")
    print(f"[DRY-RUN] Image size: {len(image_bytes):,} bytes")
    print("\n[DRY-RUN] Report:\n" + report)


# ──────────────────────────────────────────────────────────────
# 10. ENTRY POINT
# ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Radar Edge Detection Telegram Bot (SKN-240)")
    parser.add_argument("--test", action="store_true",
                        help="Dry-run: save test_radar_output.png (no Telegram token needed)")
    parser.add_argument("x", nargs="?", type=int, default=DEFAULT_USER_X,
                        help=f"Pixel X for dry-run (default: {DEFAULT_USER_X})")
    parser.add_argument("y", nargs="?", type=int, default=DEFAULT_USER_Y,
                        help=f"Pixel Y for dry-run (default: {DEFAULT_USER_Y})")
    args = parser.parse_args()

    if args.test:
        asyncio.run(_dry_run_test(args.x, args.y))
        return

    try:
        import telegram  # noqa: F401
    except ImportError:
        print(
            "ERROR: python-telegram-bot not installed.\n"
            "Install: pip install 'python-telegram-bot[job-queue]>=20.0'\n"
            "Or dry-run: python radar_bot.py --test"
        )
        sys.exit(1)

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print(
            "ERROR: TELEGRAM_BOT_TOKEN not set.\n"
            "Example: TELEGRAM_BOT_TOKEN=123:ABC python radar_bot.py\n"
            "Or dry-run: python radar_bot.py --test"
        )
        sys.exit(1)

    app = build_telegram_app()
    logger.info("🛰️  Radar Bot started (polling mode)...")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
