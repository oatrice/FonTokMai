# backend/tests/test_nationwide_radar.py

import pytest
from app.services.tmd_radar_config import STATIONS, BoundingBox

def test_nationwide_stations_present():
    """Ensure key regional TMD radar stations are configured across Thailand."""
    required_stations = [
        "kkn120", "kkn240", "skn240", # Northeast
        "svp240", "ntp240", "chn",    # Central / Bangkok Metro / Chainat
        "cmi240", "phs240",           # North
        "ubn240",                     # East Northeast
        "srt240", "pkt240"            # South
    ]
    for code in required_stations:
        assert code in STATIONS, f"Station {code} missing from STATIONS registry"
        st = STATIONS[code]
        assert st.code == code
        assert st.center_lat != 0.0
        assert st.center_lng != 0.0
        assert st.radius_km > 0.0
        assert isinstance(st.bbox, BoundingBox)

def test_chainat_preset_in_catalog():
    """Verify Chainat (chn) preset is present in KNOWN_TMD_RADAR_PRESETS."""
    from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
    chn_preset = next((p for p in KNOWN_TMD_RADAR_PRESETS if p["code"] == "chn"), None)
    assert chn_preset is not None, "Chainat (chn) preset missing from KNOWN_TMD_RADAR_PRESETS"
    assert chn_preset["center_lat"] == 15.1833
    assert chn_preset["center_lng"] == 100.1167
    assert chn_preset["radius_km"] == 240.0
    assert chn_preset["static_image_url"] == "https://weather.tmd.go.th/chn/chn240_latest.gif"
    assert chn_preset["loop_page_url"] == "https://weather.tmd.go.th/chn.php"
    assert chn_preset["loop_gif_url"] == "https://weather.tmd.go.th/chn/chnloop.gif"

def test_bounding_box_validity():
    """Verify all bounding boxes have max > min for lat and lng."""
    for code, st in STATIONS.items():
        assert st.bbox.lat_max > st.bbox.lat_min, f"Invalid lat bbox for {code}"
        assert st.bbox.lng_max > st.bbox.lng_min, f"Invalid lng bbox for {code}"
