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
    # Direct URL to Loop GIF (if available). Empty string means no loop GIF → fallback to static.
    # Verified against TMD server: kkn120 has no loop GIF, only 240km variants have loop GIFs.
    loop_gif_url: str = ""
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
    min_area_km2: float = 10.0
    legend_bboxes: list = None

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
    lat_max=19.32, 
    lng_min=101.95, 
    lat_min=15.00, 
    lng_max=106.35
)

# KKN 240km Center: ~16.43, 102.83
KKN240_BBOX = BoundingBox(
    lat_max=18.59, 
    lng_min=100.67, 
    lat_min=14.27, 
    lng_max=104.99
)

# Bounding Boxes for Nationwide TMD Stations (~240km radius, ~2.16 deg offset)
SVP240_BBOX = BoundingBox(lat_max=15.85, lng_min=98.59, lat_min=11.53, lng_max=102.91)
NTP240_BBOX = BoundingBox(lat_max=16.03, lng_min=98.37, lat_min=11.71, lng_max=102.69)
CMI240_BBOX = BoundingBox(lat_max=20.93, lng_min=96.81, lat_min=16.61, lng_max=101.13)
PHS240_BBOX = BoundingBox(lat_max=18.94, lng_min=98.11, lat_min=14.62, lng_max=102.43)
UBN240_BBOX = BoundingBox(lat_max=17.41, lng_min=102.72, lat_min=13.09, lng_max=107.04)
SRT240_BBOX = BoundingBox(lat_max=11.29, lng_min=97.02, lat_min=6.97, lng_max=101.34)
PKT240_BBOX = BoundingBox(lat_max=10.04, lng_min=96.16, lat_min=5.72, lng_max=100.48)
CHN240_BBOX = BoundingBox(lat_max=17.35, lng_min=97.88, lat_min=13.02, lng_max=102.36)

STATIONS = {
    "chn": StationConfig(
        code="chn",
        name="Chainat (240km) / ชัยนาท",
        static_image_url="https://weather.tmd.go.th/chn/chn240_latest.gif",
        loop_page_url="https://weather.tmd.go.th/chn.php",
        loop_gif_url="https://weather.tmd.go.th/chn/chnloop.gif",
        bbox=CHN240_BBOX,
        projection_type="azimuthal",
        center_lat=15.158238,
        center_lng=100.191207,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728,
    ),
    "kkn120": StationConfig(
        code="kkn120",
        name="Khon Kaen (120km)",
        static_image_url="https://weather.tmd.go.th/kkn/kkn120_latest.gif",
        loop_page_url="https://weather.tmd.go.th/kknLoop.php",
        loop_gif_url="",
        bbox=KKN_BBOX,
        projection_type="azimuthal",
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
        loop_crop_height=600,
        legend_bboxes=[(730, 100, 800, 750), (0, 740, 800, 800), (0, 0, 400, 60)]
    ),
    "kkn240": StationConfig(
        code="kkn240",
        name="Khon Kaen (240km)",
        static_image_url="https://weather.tmd.go.th/kkn/kkn240_latest.gif",
        loop_page_url="https://weather.tmd.go.th/kknLoop.php",
        loop_gif_url="https://weather.tmd.go.th/kkn/kknloop.gif",
        bbox=KKN240_BBOX,
        projection_type="azimuthal",
        center_lat=16.4322,
        center_lng=102.8236,
        radius_km=240.0,
        static_crop_x=80,
        static_crop_y=40,
        static_crop_width=720,
        static_crop_height=720,
        loop_crop_x=80,
        loop_crop_y=40,
        loop_crop_width=720,
        loop_crop_height=720,
        legend_bboxes=[(730, 100, 800, 750), (0, 740, 800, 800), (0, 0, 400, 60)]
    ),
    "skn240": StationConfig(
        code="skn240",
        name="Sakon Nakhon (240km)",
        static_image_url="https://weather.tmd.go.th/skn/skn240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/sknLoop.php",
        loop_gif_url="https://weather.tmd.go.th/skn/sknloop.gif",
        bbox=SKN_BBOX,
        projection_type="azimuthal",
        center_lat=17.1607,
        center_lng=104.1486,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728,
        legend_bboxes=[(50, 100, 75, 650), (0, 740, 800, 800), (0, 0, 400, 60)]
    ),
    "svp240": StationConfig(
        code="svp240",
        name="Bangkok Suvarnabhumi (240km)",
        static_image_url="https://weather.tmd.go.th/svp/svp240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/svpLoop.php",
        loop_gif_url="https://weather.tmd.go.th/svp/svp240_HQ_Loop.gif",
        bbox=SVP240_BBOX,
        projection_type="azimuthal",
        center_lat=13.6860,
        center_lng=100.7486,
        radius_km=240.0,
        static_crop_x=267,
        static_crop_y=197,
        static_crop_width=402,
        static_crop_height=402,
        loop_crop_x=267,
        loop_crop_y=197,
        loop_crop_width=402,
        loop_crop_height=402
    ),
    "ntp240": StationConfig(
        code="ntp240",
        name="Nonthaburi / Don Mueang (240km)",
        static_image_url="https://weather.tmd.go.th/ntp/ntp240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/ntpLoop.php",
        loop_gif_url="https://weather.tmd.go.th/ntp/ntploop.gif",
        bbox=NTP240_BBOX,
        projection_type="azimuthal",
        center_lat=13.87,
        center_lng=100.53,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
    ),
    "cmi240": StationConfig(
        code="cmi240",
        name="Chiang Mai (240km)",
        static_image_url="https://weather.tmd.go.th/cmi/cmi240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/cmiLoop.php",
        loop_gif_url="https://weather.tmd.go.th/cmi/cmiloop.gif",
        bbox=CMI240_BBOX,
        projection_type="azimuthal",
        center_lat=18.77,
        center_lng=98.97,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
    ),
    "phs240": StationConfig(
        code="phs240",
        name="Phitsanulok (240km)",
        static_image_url="https://weather.tmd.go.th/phs/phs240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/phsLoop.php",
        loop_gif_url="https://weather.tmd.go.th/phs/phsloop.gif",
        bbox=PHS240_BBOX,
        projection_type="azimuthal",
        center_lat=16.78,
        center_lng=100.27,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
    ),
    "ubn240": StationConfig(
        code="ubn240",
        name="Ubon Ratchathani (240km)",
        static_image_url="https://weather.tmd.go.th/ubn/ubn240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/ubnLoop.php",
        loop_gif_url="https://weather.tmd.go.th/ubn/ubnloop.gif",
        bbox=UBN240_BBOX,
        projection_type="azimuthal",
        center_lat=15.25,
        center_lng=104.88,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
    ),
    "srt240": StationConfig(
        code="srt240",
        name="Surat Thani (240km)",
        static_image_url="https://weather.tmd.go.th/srt/srt240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/srtLoop.php",
        loop_gif_url="https://weather.tmd.go.th/srt/srtloop.gif",
        bbox=SRT240_BBOX,
        projection_type="azimuthal",
        center_lat=9.13,
        center_lng=99.18,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
    ),
    "pkt240": StationConfig(
        code="pkt240",
        name="Phuket (240km)",
        static_image_url="https://weather.tmd.go.th/pkt/pkt240_latest.jpg",
        loop_page_url="https://weather.tmd.go.th/pktLoop.php",
        loop_gif_url="https://weather.tmd.go.th/pkt/pktloop.gif",
        bbox=PKT240_BBOX,
        projection_type="azimuthal",
        center_lat=7.88,
        center_lng=98.32,
        radius_km=240.0,
        static_crop_x=72,
        static_crop_y=28,
        static_crop_width=728,
        static_crop_height=728,
        loop_crop_x=72,
        loop_crop_y=28,
        loop_crop_width=728,
        loop_crop_height=728
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
    # Light Green (15-20 dBZ)
    (0, 255, 0): 20.0,
    (4, 248, 3): 20.0,
    (13, 239, 13): 20.0,
    (4, 231, 2): 20.0,
    (36, 212, 41): 20.0,
    (6, 207, 6): 20.0,
    (81, 212, 89): 20.0,
    (95, 157, 97): 20.0,    # Faint green (JPEG artifact from C4)
    (60, 180, 60): 20.0,    # JPEG artifact green mid
    (45, 195, 45): 20.0,    # JPEG artifact green bright
    (70, 200, 70): 20.0,    # JPEG artifact green bright-2
    (50, 170, 55): 20.0,    # JPEG artifact green-yellow tinge
    # Green (25-30 dBZ)
    (0, 128, 0): 25.0,
    (73, 160, 71): 25.0,
    (42, 157, 37): 25.0,
    (88, 171, 81): 25.0,
    (5, 174, 5): 25.0,
    (84, 198, 52): 25.0,
    (86, 138, 74): 25.0,    # Green (JPEG artifact from C4)
    (55, 145, 55): 25.0,    # JPEG artifact dark green
    (65, 155, 62): 25.0,    # JPEG artifact dark green-2
    # Yellow-green (30 dBZ transition)
    (150, 200, 50): 30.0,
    (160, 210, 40): 30.0,
    (140, 195, 60): 30.0,
    # Yellow (35-40 dBZ)
    (255, 255, 0): 35.0,
    (248, 248, 4): 35.0,
    (241, 242, 12): 35.0,
    (224, 224, 37): 35.0,
    (215, 217, 91): 35.0,
    # Orange (45 dBZ)
    (255, 128, 0): 45.0,
    (235, 153, 6): 45.0,
    (243, 168, 14): 45.0,
    (220, 154, 26): 45.0,
    (250, 167, 3): 45.0,
    # Red (50-55 dBZ)
    (255, 0, 0): 50.0,
    (239, 2, 2): 50.0,
    (198, 2, 2): 55.0,
    (214, 4, 3): 50.0,
    (169, 5, 5): 55.0,
    (220, 40, 10): 50.0,
    # Purple / Magenta
    (255, 0, 255): 60.0,
}

# Background colors to ignore (Map backgrounds, borders, text, white/gray)
IGNORED_COLORS = [
    (255, 255, 255), # White
    (0, 0, 0),       # Black
    (204, 204, 204), # Gray
    (32, 45, 93),    # Dark brown/grey map background
    (153, 153, 153), # Gray
    # Add actual map background RGB here during calibration
    (110, 127, 91),  # Map background green 1
    (108, 125, 89),  # Map background green 2
    (87, 156, 73),   # Map background bright green 1
    (79, 151, 67),   # Map background bright green 2
    (84, 148, 89),   # Map background bright green 3
    # Additional problematic map pixels
    (77, 159, 74),
    (61, 156, 64),
    (66, 172, 71),
    (75, 169, 73),
    (73, 170, 77),
    (68, 159, 64),
    (77, 162, 79),
    (67, 156, 74),
    (77, 156, 77),
    (65, 159, 71),
    (66, 156, 68),
    (79, 160, 67),
    (71, 161, 73),
    (76, 161, 78),
    (69, 155, 84),
    # River / Lake / Sea background blue/cyan colors
    (62, 101, 144),  # Water body / lake blue
    (75, 149, 169),  # Water body cyan
    (52, 139, 153),  # Water body dark cyan
    (53, 147, 174),  # Water body light cyan
    (176, 217, 239), # Water body soft blue
    (210, 237, 247), # Water body very soft blue
    (231, 243, 243), # Water body white-blue
    (104, 180, 182), # Water body bright cyan
    (107, 156, 168), # Water body grey-cyan
    (79, 112, 169),  # Mekong River blue
    (84, 115, 139),  # Mekong River dark grey-blue
    (53, 83, 112),   # Mekong River deep blue
    (67, 101, 149),  # Mekong River blue-purple
    (203, 217, 238), # Mekong River light blue
    (90, 118, 71),   # Terrain green-brown (kkn240)
    (86, 139, 75),   # Terrain green (kkn240)
]

