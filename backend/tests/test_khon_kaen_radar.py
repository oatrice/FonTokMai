# backend/tests/test_khon_kaen_radar.py
#
# Comprehensive regression guard for the Khon Kaen 240km (kkn240) radar station
# and the "home" Thabo, Nong Khai pin.
#
# WHY THIS FILE EXISTS
# --------------------
# Adding or tuning radar stations has repeatedly caused subtle drift in the
# kkn240 coordinate system. These tests lock down every layer of the pipeline:
#
#   1. Config integrity           - crop offsets, center lat/lng, radius
#   2. Center-pin exactness       - center maps to pixel (362, 362) on crop
#   3. Thabo regression pin       - offset math and crop-frame transform
#   4. Multi-point directionality - N/S/E/W pins land in correct quadrant
#   5. Out-of-bounds rejection    - points outside bbox return (None, None)
#   6. Neon DB preset alignment   - fallback preset matches hardcoded config
#   7. BBox coverage              - kkn240 covers all expected Thai provinces
#   8. Terrain color filtering    - kkn240 terrain greens NOT counted as rain
#   9. Rain color detection       - real rain colors ARE detected
#  10. Legacy full-frame scaling  - re-projection to 800x800 full frame
#  11. Scale invariance           - crop offsets removed correctly for any crop

import math
import numpy as np
import pytest

from app.services.tmd_radar_config import STATIONS, BoundingBox, IGNORED_COLORS, DBZ_COLOR_MAPPING
from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
from app.services.tmd_radar.processor import TMDRadarProcessor
from app.services.tmd_radar.clustering import TMDClusteringMixin

# ---------------------------------------------------------------------------
# Constants (ground truth) - change ONLY after deliberate calibration
# ---------------------------------------------------------------------------
KKN240_CENTER_LAT = 16.4322
KKN240_CENTER_LNG = 102.8236
KKN240_RADIUS_KM  = 240.0
KKN240_CROP_X     = 71
KKN240_CROP_Y     = 29
KKN240_CROP_W     = 724
KKN240_CROP_H     = 724
KKN240_HALF_PX    = KKN240_CROP_W // 2  # 362

# "Home" location - Thabo District, Nong Khai
THABO_LAT = 17.8392
THABO_LNG = 102.5734
# Expected pixel on 724x724 cropped frame (verified against Telegram output)
THABO_CROP_PX = 322
THABO_CROP_PY = 125

# Tolerance for pixel assertions (+-1 px rounding)
TOL = 1


# ===========================================================================
# 1. CONFIG INTEGRITY
# ===========================================================================

class TestKkn240ConfigIntegrity:
    """Lock down every calibrated field. ANY change here must be intentional."""

    def test_station_exists(self):
        assert "kkn240" in STATIONS, (
            "Station 'kkn240' is missing from STATIONS. "
            "If it was renamed or deleted, update tmd_radar_config.py deliberately."
        )

    def test_station_code(self):
        assert STATIONS["kkn240"].code == "kkn240"

    def test_station_name(self):
        assert STATIONS["kkn240"].name == "Khon Kaen (240km)"

    def test_center_lat(self):
        assert STATIONS["kkn240"].center_lat == KKN240_CENTER_LAT, (
            f"center_lat changed from {KKN240_CENTER_LAT}! "
            "Changing center_lat shifts ALL pin calculations for kkn240. "
            "Update KKN240_CENTER_LAT only after deliberate calibration."
        )

    def test_center_lng(self):
        assert STATIONS["kkn240"].center_lng == KKN240_CENTER_LNG, (
            f"center_lng changed from {KKN240_CENTER_LNG}! "
            "Changing center_lng shifts ALL pin calculations for kkn240. "
            "Update KKN240_CENTER_LNG only after deliberate calibration."
        )

    def test_radius_km(self):
        assert STATIONS["kkn240"].radius_km == KKN240_RADIUS_KM

    def test_static_crop_offsets(self):
        st = STATIONS["kkn240"]
        assert st.static_crop_x == KKN240_CROP_X, (
            f"static_crop_x changed from {KKN240_CROP_X}! "
            "This shifts the radar center crosshair in radar_latest.jpg. "
            "Update KKN240_CROP_X only after deliberate calibration."
        )
        assert st.static_crop_y == KKN240_CROP_Y, (
            f"static_crop_y changed from {KKN240_CROP_Y}! "
            "Update KKN240_CROP_Y only after deliberate calibration."
        )
        assert st.static_crop_width  == KKN240_CROP_W
        assert st.static_crop_height == KKN240_CROP_H

    def test_loop_crop_offsets_match_static(self):
        """Loop crop must match static crop for kkn240."""
        st = STATIONS["kkn240"]
        assert st.loop_crop_x      == KKN240_CROP_X
        assert st.loop_crop_y      == KKN240_CROP_Y
        assert st.loop_crop_width  == KKN240_CROP_W
        assert st.loop_crop_height == KKN240_CROP_H

    def test_projection_type(self):
        assert STATIONS["kkn240"].projection_type == "azimuthal"

    def test_bbox_type(self):
        assert isinstance(STATIONS["kkn240"].bbox, BoundingBox)

    def test_urls_present(self):
        st = STATIONS["kkn240"]
        assert "kkn240_latest" in st.static_image_url
        assert st.loop_gif_url.startswith("https://")
        assert st.loop_page_url.startswith("https://")


# ===========================================================================
# 2. CENTER-PIN EXACTNESS
# ===========================================================================

class TestKkn240CenterPin:
    """The radar antenna center must map exactly to the geometric center of the crop."""

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    def test_center_maps_to_crop_midpoint_loop(self):
        px, py = self.proc.latlng_to_pixel(
            KKN240_CENTER_LAT, KKN240_CENTER_LNG,
            is_loop=True, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )
        assert px == KKN240_HALF_PX, (
            f"Radar center X off: expected {KKN240_HALF_PX}, got {px}. "
            "Crop offset or center_lat/lng may have been mis-tuned."
        )
        assert py == KKN240_HALF_PX, (
            f"Radar center Y off: expected {KKN240_HALF_PX}, got {py}. "
            "Crop offset or center_lat/lng may have been mis-tuned."
        )

    def test_center_maps_to_crop_midpoint_static(self):
        px, py = self.proc.latlng_to_pixel(
            KKN240_CENTER_LAT, KKN240_CENTER_LNG,
            is_loop=False, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )
        assert px == KKN240_HALF_PX
        assert py == KKN240_HALF_PX

    def test_center_full_frame_includes_crop_offsets(self):
        """Without frame_shape, px/py include the raw crop offsets."""
        px, py = self.proc.latlng_to_pixel(
            KKN240_CENTER_LAT, KKN240_CENTER_LNG, is_loop=False
        )
        expected_x = KKN240_CROP_X + KKN240_HALF_PX  # 71 + 362 = 433
        expected_y = KKN240_CROP_Y + KKN240_HALF_PX  # 29 + 362 = 391
        assert abs(px - expected_x) <= TOL, f"Full-frame center X: expected ~{expected_x}, got {px}"
        assert abs(py - expected_y) <= TOL, f"Full-frame center Y: expected ~{expected_y}, got {py}"


# ===========================================================================
# 3. THABO REGRESSION PIN
# ===========================================================================

class TestThaboPinRegression:
    """
    Thabo District, Nong Khai (17.8392, 102.5734) is the canonical 'home'
    location used in production. These tests must NEVER silently regress.
    """

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    def test_thabo_crop_pixel_exact(self):
        """Thabo maps to expected pixel on a 724x724 cropped frame."""
        px, py = self.proc.latlng_to_pixel(
            THABO_LAT, THABO_LNG,
            is_loop=True, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )
        assert abs(px - THABO_CROP_PX) <= TOL, (
            f"Thabo X regression: expected {THABO_CROP_PX} +/- {TOL}, got {px}. "
            "If crop offsets or center_lat/lng changed, verify radar_latest.jpg "
            "visually and update THABO_CROP_PX."
        )
        assert abs(py - THABO_CROP_PY) <= TOL, (
            f"Thabo Y regression: expected {THABO_CROP_PY} +/- {TOL}, got {py}. "
            "If crop offsets or center_lat/lng changed, verify radar_latest.jpg "
            "visually and update THABO_CROP_PY."
        )

    def test_thabo_crop_offset_arithmetic(self):
        """crop-frame pixel = full-frame pixel minus crop offsets."""
        px_full, py_full = self.proc.latlng_to_pixel(THABO_LAT, THABO_LNG, is_loop=False)
        px_crop, py_crop = self.proc.latlng_to_pixel(
            THABO_LAT, THABO_LNG,
            is_loop=False, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )
        assert px_crop == px_full - KKN240_CROP_X, (
            f"Crop-offset X arithmetic broke: {px_full} - {KKN240_CROP_X} != {px_crop}"
        )
        assert py_crop == py_full - KKN240_CROP_Y, (
            f"Crop-offset Y arithmetic broke: {py_full} - {KKN240_CROP_Y} != {py_crop}"
        )

    def test_thabo_not_none(self):
        """Thabo must never return (None, None) -- it is inside kkn240 bbox."""
        px, py = self.proc.latlng_to_pixel(THABO_LAT, THABO_LNG, is_loop=True)
        assert px is not None and py is not None, (
            "Thabo returned None! It may have been excluded by a bbox change. "
            "Check tmd_radar_config.py KKN240_BBOX."
        )

    def test_thabo_within_radar_circle(self):
        """Thabo is ~159 km from center, well within 240 km radius."""
        px, py = self.proc.latlng_to_pixel(
            THABO_LAT, THABO_LNG,
            is_loop=True, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )
        dist_px = math.hypot(px - KKN240_HALF_PX, py - KKN240_HALF_PX)
        dist_km = dist_px * KKN240_RADIUS_KM / KKN240_HALF_PX
        assert dist_km < KKN240_RADIUS_KM, f"Thabo appears outside radar circle: {dist_km:.1f} km"
        assert dist_km > 100, f"Thabo suspiciously close to center: {dist_km:.1f} km (expected ~159 km)"


# ===========================================================================
# 4. MULTI-POINT DIRECTIONALITY
# ===========================================================================

class TestKkn240Directionality:
    """
    Verify that N/S/E/W points land in the correct image quadrant.
    A sign error in bearing math would flip the entire map.
    """

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    def _crop_px(self, lat, lng):
        return self.proc.latlng_to_pixel(
            lat, lng, is_loop=True, frame_shape=(KKN240_CROP_H, KKN240_CROP_W)
        )

    def test_north_of_center_has_lower_py(self):
        """In image coords Y increases downward, so north = smaller Y."""
        _, py = self._crop_px(KKN240_CENTER_LAT + 1.0, KKN240_CENTER_LNG)
        assert py < KKN240_HALF_PX, f"North pin Y={py} should be < {KKN240_HALF_PX}"

    def test_south_of_center_has_higher_py(self):
        _, py = self._crop_px(KKN240_CENTER_LAT - 1.0, KKN240_CENTER_LNG)
        assert py > KKN240_HALF_PX, f"South pin Y={py} should be > {KKN240_HALF_PX}"

    def test_east_of_center_has_higher_px(self):
        px, _ = self._crop_px(KKN240_CENTER_LAT, KKN240_CENTER_LNG + 1.0)
        assert px > KKN240_HALF_PX, f"East pin X={px} should be > {KKN240_HALF_PX}"

    def test_west_of_center_has_lower_px(self):
        px, _ = self._crop_px(KKN240_CENTER_LAT, KKN240_CENTER_LNG - 1.0)
        assert px < KKN240_HALF_PX, f"West pin X={px} should be < {KKN240_HALF_PX}"

    def test_thabo_is_north_west_of_center(self):
        """Thabo (17.84N, 102.57E) is NW of center (16.43N, 102.82E)."""
        px, py = self._crop_px(THABO_LAT, THABO_LNG)
        assert py < KKN240_HALF_PX, f"Thabo should be north of center (py<362), got py={py}"
        assert px < KKN240_HALF_PX, f"Thabo should be west of center (px<362), got px={px}"

    def test_khonkaen_city_near_center(self):
        """Khon Kaen city (16.44N, 102.84E) is very close to radar center."""
        px, py = self._crop_px(16.4419, 102.8360)
        dist_px = math.hypot(px - KKN240_HALF_PX, py - KKN240_HALF_PX)
        assert dist_px < 10, f"KhonKaen city should be within 10px of center, got {dist_px:.1f}px"

    def test_udon_thani_is_north(self):
        """Udon Thani (17.42N, 102.79E) is north of center."""
        _, py = self._crop_px(17.4156, 102.7875)
        assert py < KKN240_HALF_PX, f"Udon Thani should be north of center, got py={py}"

    def test_nong_khai_further_north_than_udon(self):
        """Nong Khai is further north than Udon Thani, so py should be smaller."""
        _, py_nk = self._crop_px(17.8726, 102.7420)
        _, py_ud = self._crop_px(17.4156, 102.7875)
        assert py_nk < py_ud, (
            f"Nong Khai (py={py_nk}) should be higher in image than Udon Thani (py={py_ud})"
        )


# ===========================================================================
# 5. OUT-OF-BOUNDS REJECTION
# ===========================================================================

class TestKkn240OutOfBounds:
    """Points outside the kkn240 bounding box must return (None, None)."""

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    @pytest.mark.parametrize("lat,lng,desc", [
        (0.0,    0.0,   "Null Island"),
        (22.0,  102.0,  "Far north of bbox"),
        (14.0,  102.0,  "South of bbox lat_min"),
        (16.4,  100.0,  "West of bbox lng_min"),
        (16.4,  105.5,  "East of bbox lng_max"),
        (90.0,  102.8,  "North Pole"),
        (-90.0, 102.8,  "South Pole"),
    ])
    def test_out_of_bounds_returns_none(self, lat, lng, desc):
        px, py = self.proc.latlng_to_pixel(lat, lng, is_loop=False)
        assert px is None and py is None, (
            f"{desc} ({lat},{lng}) should be out of bounds, but got px={px}, py={py}"
        )


# ===========================================================================
# 6. NEON DB PRESET ALIGNMENT
# ===========================================================================

class TestKkn240PresetAlignment:
    """
    The Neon DB preset (KNOWN_TMD_RADAR_PRESETS) is the fallback when dynamic
    config is missing. It must mirror the hardcoded config exactly.
    """

    def test_preset_exists(self):
        preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240"), None)
        assert preset is not None, "'kkn240' missing from KNOWN_TMD_RADAR_PRESETS"

    def test_preset_center_lat_matches(self):
        preset = next(p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240")
        assert preset["center_lat"] == STATIONS["kkn240"].center_lat, (
            "KNOWN_TMD_RADAR_PRESETS center_lat doesn't match STATIONS! "
            "Update both sources together to keep Neon DB fallback in sync."
        )

    def test_preset_center_lng_matches(self):
        preset = next(p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240")
        assert preset["center_lng"] == STATIONS["kkn240"].center_lng

    def test_preset_radius_km_matches(self):
        preset = next(p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240")
        assert preset["radius_km"] == STATIONS["kkn240"].radius_km

    def test_preset_crop_offsets_match(self):
        preset = next(p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "kkn240")
        st = STATIONS["kkn240"]
        crop_x = preset.get("crop_x", preset.get("static_crop_x", KKN240_CROP_X))
        crop_y = preset.get("crop_y", preset.get("static_crop_y", KKN240_CROP_Y))
        assert crop_x == st.static_crop_x
        assert crop_y == st.static_crop_y


# ===========================================================================
# 7. BBOX COVERAGE
# ===========================================================================

class TestKkn240BboxCoverage:
    """kkn240 bbox should cover all expected provinces in its 240 km scan area."""

    def setup_method(self):
        self.bbox = STATIONS["kkn240"].bbox

    def _in_bbox(self, lat, lng):
        return (
            self.bbox.lat_min <= lat <= self.bbox.lat_max and
            self.bbox.lng_min <= lng <= self.bbox.lng_max
        )

    @pytest.mark.parametrize("name,lat,lng", [
        ("Khon Kaen",     16.4419, 102.8360),
        ("Udon Thani",    17.4156, 102.7875),
        ("Nong Khai",     17.8726, 102.7420),
        ("Thabo",         THABO_LAT, THABO_LNG),
        ("Roi Et",        16.0538, 103.6520),
        ("Kalasin",       16.4322, 103.5062),
        ("Maha Sarakham", 16.1847, 103.3000),
        ("Loei",          17.4869, 101.7225),
    ])
    def test_province_inside_bbox(self, name, lat, lng):
        assert self._in_bbox(lat, lng), (
            f"{name} ({lat},{lng}) should be inside kkn240 bbox "
            f"(lat=[{self.bbox.lat_min},{self.bbox.lat_max}], "
            f"lng=[{self.bbox.lng_min},{self.bbox.lng_max}])"
        )


# ===========================================================================
# 8. TERRAIN COLOR FILTERING
# ===========================================================================

class TestKkn240TerrainFiltering:
    """kkn240-specific terrain/ground colors must NOT be counted as rain."""

    def setup_method(self):
        self.proc  = TMDRadarProcessor(station_code="kkn240")
        self.mixin = TMDClusteringMixin()

    @pytest.mark.parametrize("color", [
        (90, 118, 71),
        (86, 139, 75),
        (86, 138, 74),
        (92, 130, 72),
        (85, 140, 72),
    ])
    def test_terrain_not_rain_scalar(self, color):
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[5, 5] = color
        dbz = self.proc.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz == 0.0, (
            f"Terrain color {color} wrongly detected as {dbz} dBZ. "
            "Add it to IGNORED_COLORS in tmd_radar_config.py."
        )

    @pytest.mark.parametrize("color", [
        (90, 118, 71),
        (86, 139, 75),
    ])
    def test_terrain_not_rain_vectorized(self, color):
        frame   = np.full((20, 20, 3), color, dtype=np.uint8)
        raw_map = self.mixin._extract_raw_dbz_map(frame)
        mask    = self.mixin.extract_rain_mask(frame)
        assert np.max(raw_map) == 0.0, f"_extract_raw_dbz_map detected terrain {color} as rain"
        assert np.max(mask) == 0,      f"extract_rain_mask masked terrain {color} as rain"

    def test_ignored_colors_list_not_empty(self):
        assert len(IGNORED_COLORS) > 0, "IGNORED_COLORS should not be empty"


# ===========================================================================
# 9. RAIN COLOR DETECTION
# ===========================================================================

class TestKkn240RainDetection:
    """Legitimate radar echoes must always be detected in kkn240 frames."""

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    @pytest.mark.parametrize("color,min_dbz", [
        ((0,   255, 0),   20.0),   # Radar green  ~20 dBZ
        ((4,   248, 3),   20.0),   # Typical scan green
        ((255, 255, 0),   35.0),   # Yellow       ~35 dBZ
        ((255, 128, 0),   45.0),   # Orange       ~45 dBZ
        ((255, 0,   0),   50.0),   # Red          ~50 dBZ
    ])
    def test_rain_color_detected(self, color, min_dbz):
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        img[5, 5] = color
        dbz = self.proc.get_dbz_at_pixel(img, x=5, y=5)
        assert dbz >= min_dbz, (
            f"Rain color {color} ignored (got {dbz} dBZ, expected >= {min_dbz}). "
            "Check DBZ_COLOR_MAPPING in tmd_radar_config.py."
        )

    def test_dbz_color_mapping_not_empty(self):
        assert len(DBZ_COLOR_MAPPING) > 0, "DBZ_COLOR_MAPPING should not be empty"


# ===========================================================================
# 10. LEGACY FULL-FRAME RE-PROJECTION (800x800)
# ===========================================================================

class TestKkn240LegacyFrameScaling:
    """
    Firestore may cache full 800x800 frames (pre-crop). The processor must
    re-project correctly so old cached frames still show the pin correctly.
    """

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    def test_thabo_full_frame_valid_pixel(self):
        px, py = self.proc.latlng_to_pixel(
            THABO_LAT, THABO_LNG, is_loop=False, frame_shape=(800, 800)
        )
        assert px is not None and py is not None
        assert 0 <= px < 800 and 0 <= py < 800, f"Pixel out of 800x800 canvas: ({px},{py})"

    def test_center_full_frame_near_crosshair(self):
        """On 800x800 full frame, kkn240 center re-projects with non-uniform scaling.
        config_canvas = (crop_x + crop_w) x (crop_y + crop_h) = 795 x 753.
        Scaled to 800x800: center_x = 433 * (800/795) = 436, center_y = 391 * (800/753) = 415.
        """
        px, py = self.proc.latlng_to_pixel(
            KKN240_CENTER_LAT, KKN240_CENTER_LNG,
            is_loop=False, frame_shape=(800, 800)
        )
        assert px is not None and py is not None
        # Re-projected center accounting for non-uniform X/Y scale
        config_canvas_w = KKN240_CROP_X + KKN240_CROP_W  # 795
        config_canvas_h = KKN240_CROP_Y + KKN240_CROP_H  # 753
        radar_cx = KKN240_CROP_X + KKN240_HALF_PX        # 433
        radar_cy = KKN240_CROP_Y + KKN240_HALF_PX        # 391
        import math
        expected_x = round(radar_cx * 800 / config_canvas_w)  # 436
        expected_y = round(radar_cy * 800 / config_canvas_h)  # 415
        assert abs(px - expected_x) <= 3, f"Center X on 800x800: expected ~{expected_x}, got {px}"
        assert abs(py - expected_y) <= 3, f"Center Y on 800x800: expected ~{expected_y}, got {py}"



# ===========================================================================
# 11. SCALE INVARIANCE
# ===========================================================================

class TestKkn240ScaleInvariance:
    """
    When frame_shape matches crop dimensions (+-4 px), processor strips crop
    offsets. Verify for minor JPEG re-encoding size variations.
    """

    def setup_method(self):
        self.proc = TMDRadarProcessor(station_code="kkn240")

    @pytest.mark.parametrize("h,w", [
        (724, 724),  # Exact match
        (722, 722),  # 2px smaller
        (726, 726),  # 2px larger
        (728, 728),  # 4px larger (boundary of tolerance)
    ])
    def test_crop_offset_stripped(self, h, w):
        px, py = self.proc.latlng_to_pixel(
            KKN240_CENTER_LAT, KKN240_CENTER_LNG,
            is_loop=True, frame_shape=(h, w)
        )
        assert abs(px - w // 2) <= 5, f"Center X for {w}x{h}: expected ~{w//2}, got {px}"
        assert abs(py - h // 2) <= 5, f"Center Y for {w}x{h}: expected ~{h//2}, got {py}"
