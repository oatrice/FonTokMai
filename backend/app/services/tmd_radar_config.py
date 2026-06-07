# backend/app/services/tmd_radar_config.py

from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class BoundingBox:
    lat_max: float  # Top
    lng_min: float  # Left
    lat_min: float  # Bottom
    lng_max: float  # Right

@dataclass
class StationConfig:
    code: str
    name: str
    static_image_url: str
    loop_page_url: str
    bbox: BoundingBox
    # These represent the pixel coordinates within the downloaded image
    # where the actual map (excluding titles/legends) starts and ends.
    # We use approximate whole-image values for now until calibrated.
    # Static Image Crop (for _latest.gif which is usually ~800x800)
    static_crop_x: int = 0
    static_crop_y: int = 0
    static_crop_width: int = 800
    static_crop_height: int = 800

    # Loop Image Crop (for Loop.gif which is usually compressed to 680x680)
    loop_crop_x: int = 0
    loop_crop_y: int = 0
    loop_crop_width: int = 680
    loop_crop_height: int = 680
    projection_type: str = "linear"  # "linear" or "azimuthal"
    center_lat: float = 0.0
    center_lng: float = 0.0
    radius_km: float = 0.0
    # dict mapping "lat,lng" to "pixel_x,pixel_y" for affine calibration
    calibration_points: Dict[Tuple[float, float], Tuple[float, float]] = None

# Approximate bounding boxes for 120km radius.
# 1 degree is roughly 111km. 120km is ~1.08 degrees.
# KKN Center: ~16.43, 102.83
KKN_BBOX = BoundingBox(
    lat_max=17.53, 
    lng_min=101.73, 
    lat_min=15.33, 
    lng_max=103.93
)

# SKN Center: ~17.16, 104.13
SKN_BBOX = BoundingBox(
    lat_max=18.26, 
    lng_min=103.03, 
    lat_min=16.06, 
    lng_max=105.23
)

# KKN 240km Center: ~16.43, 102.83
KKN240_BBOX = BoundingBox(
    lat_max=18.59, 
    lng_min=100.67, 
    lat_min=14.27, 
    lng_max=104.99
)

STATIONS = {
    "kkn120": StationConfig(
        code="kkn120",
        name="Khon Kaen (120km)",
        static_image_url="https://weather.tmd.go.th/kkn/kkn120_latest.gif",
        loop_page_url="https://weather.tmd.go.th/kknLoop.php",
        bbox=KKN_BBOX,
        center_lat=16.4322,
        center_lng=102.8236,
        radius_km=120.0,
        static_crop_x=80,
        static_crop_y=40,
        static_crop_width=720,
        static_crop_height=720,
        loop_crop_x=80,
        loop_crop_y=40,
        loop_crop_width=600,
        loop_crop_height=600
    ),
    "kkn240": StationConfig(
        code="kkn240",
        name="Khon Kaen (240km)",
        static_image_url="https://weather.tmd.go.th/kkn/kkn240_latest.gif",
        loop_page_url="https://weather.tmd.go.th/kknLoop.php",
        bbox=KKN240_BBOX,
        center_lat=16.4322,
        center_lng=102.8236,
        radius_km=240.0,
        # Image is 680x680. Legend on left is approx 80px.
        # Radar circle is approx 600x600, vertically centered.
        static_crop_x=80,
        static_crop_y=40,
        static_crop_width=720,
        static_crop_height=720,
        loop_crop_x=80,
        loop_crop_y=40,
        loop_crop_width=600,
        loop_crop_height=600
    ),
    "skn240": StationConfig(
        code="skn240",
        name="Sakon Nakhon (240km)",
        static_image_url="https://weather.tmd.go.th/skn/skn240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/sknLoop.php",
        bbox=SKN_BBOX,
        center_lat=17.1607,
        center_lng=104.1486,
        radius_km=240.0
    )
}

# RGB to dBZ mapping (approximate standard radar colors)
# We map typical RGB tuples to dBZ values.
# Real calibration requires picking the exact RGB from the TMD legend.
DBZ_COLOR_MAPPING: Dict[Tuple[int, int, int], float] = {
    # Light Blue
    (0, 255, 255): 10.0,
    # Blue
    (0, 0, 255): 15.0,
    # Light Green
    (0, 255, 0): 20.0,
    # Green
    (0, 128, 0): 25.0,
    (73, 160, 71): 25.0, # Real GIF Green
    # Yellow
    (255, 255, 0): 35.0,
    # Orange
    (255, 128, 0): 45.0,
    # Red
    (255, 0, 0): 50.0,
    # Dark Red
    (128, 0, 0): 55.0,
    # Purple / Magenta
    (255, 0, 255): 60.0
}

# Background colors to ignore (Map backgrounds, borders, text, white/gray)
IGNORED_COLORS = [
    (255, 255, 255), # White
    (0, 0, 0),       # Black
    (204, 204, 204), # Gray
    (32, 45, 93),    # Dark brown/grey map background
    (153, 153, 153), # Gray
    # Add actual map background RGB here during calibration
]
