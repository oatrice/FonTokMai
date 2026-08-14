import pytest
from app.routers.webhook_utils import (
    _build_forecast_text,
    _build_advanced_text,
    extract_forecast_media,
    build_formatted_forecast,
    FormattedForecastResponse,
    ForecastMediaItem,
)

def test_build_forecast_text_no_rain():
    result = {"endpoint": "tmd-radar", "predictions": [], "rain_summary": None}
    text, endpoint, eta = _build_forecast_text(result)
    assert "ยังไม่มีแนวโน้มฝนตก" in text
    assert endpoint == "tmd-radar"
    assert eta is None

def test_build_forecast_text_with_rain_summary_and_growth():
    result = {
        "endpoint": "tmd-radar",
        "rain_summary": "ฝนกำลังตกปานกลาง",
        "wind_speed_kmh": 25.5,
        "wind_dir_text": "ตะวันออกเฉียงเหนือ (NE)",
        "growth_rate_pct": 12.0,
    }
    text, endpoint, eta = _build_forecast_text(result)
    assert "ฝนกำลังตกปานกลาง" in text
    assert "25.5 km/h" in text
    assert "กำลังก่อตัวแรงขึ้น (+12.0%/15min)" in text

def test_build_advanced_text_empty():
    adv_text = _build_advanced_text({})
    assert "ไม่พบประกาศเตือนภัย" in adv_text

def test_build_advanced_text_full():
    advanced_data = {
        "advisories": [{"name": "พายุฤดูร้อน"}],
        "lightning": {"distance_km": 4.5, "detected": True},
        "stormcell": {
            "distance_km": 12.0,
            "direction": "NE",
            "speed_kmh": 35.0,
            "max_dbz": 52.0
        }
    }
    adv_text = _build_advanced_text(advanced_data)
    assert "🚨 *ข้อมูลเตือนภัยขั้นสูงรอบตัวคุณ*" in adv_text
    assert "พายุฤดูร้อน" in adv_text
    assert "4.5 กม." in adv_text
    assert "12.0 กม." in adv_text
    assert "52.0" in adv_text

def test_extract_forecast_media_default_rain():
    mock_result = {
        "radar_tracking_bytes": b"tracking_png",
        "radar_gif_bytes": b"nowcast_gif",
        "radar_static_bytes": b"static_png",
        "rain_timeline_bytes": b"timeline_png",
        "radar_multiframe_bytes": b"multiframe_png",
    }
    media = extract_forecast_media(mock_result, cmd_name="/rain", show_advanced=False)
    filenames = [m.filename for m in media]
    assert "radar_tracking.png" in filenames
    assert "radar_nowcast.gif" in filenames
    assert "radar_latest.png" not in filenames

def test_extract_forecast_media_advanced_pro():
    mock_result = {
        "radar_tracking_bytes": b"tracking_png",
        "radar_static_bytes": b"static_png",
        "rain_timeline_bytes": b"timeline_png",
        "radar_multiframe_bytes": b"multiframe_png",
        "radar_hq_gif_bytes": b"hq_gif",
        "radar_gif_bytes": b"nowcast_gif",
    }
    media = extract_forecast_media(mock_result, cmd_name="/rain_pro", show_advanced=True)
    filenames = [m.filename for m in media]
    assert len(media) == 6
    assert "radar_tracking.png" in filenames
    assert "radar_latest.png" in filenames
    assert "rain_timeline.png" in filenames
    assert "radar_multiframe.png" in filenames
    assert "radar_nowcast_full.gif" in filenames
    assert "radar_nowcast.gif" in filenames

def test_extract_forecast_media_specific_commands():
    mock_result = {
        "radar_static_bytes": b"static_png",
        "radar_tracking_bytes": b"tracking_png",
        "rain_timeline_bytes": b"timeline_png",
        "radar_gif_bytes": b"nowcast_gif",
    }
    assert [m.filename for m in extract_forecast_media(mock_result, cmd_name="/radar")] == ["radar_latest.png"]
    assert [m.filename for m in extract_forecast_media(mock_result, cmd_name="/tracking")] == ["radar_tracking.png"]
    assert [m.filename for m in extract_forecast_media(mock_result, cmd_name="/timeline")] == ["rain_timeline.png"]
    assert [m.filename for m in extract_forecast_media(mock_result, cmd_name="/nowcast")] == ["radar_nowcast.gif"]

def test_build_formatted_forecast_payload():
    mock_result = {
        "endpoint": "tmd-radar",
        "rain_summary": "ฝนกำลังตก",
        "radar_tracking_bytes": b"tracking_png",
    }
    response = build_formatted_forecast(
        result=mock_result,
        cmd_name="/rain",
        show_advanced=False,
        location_name="Bangkok"
    )
    assert isinstance(response, FormattedForecastResponse)
    assert "📍 **พื้นที่:** Bangkok" in response.text
    assert response.actual_endpoint == "tmd-radar"
    assert len(response.media_items) == 1
    assert response.media_items[0].filename == "radar_tracking.png"
