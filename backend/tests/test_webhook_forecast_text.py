import pytest
from app.routers.webhook_utils import _build_forecast_text

def test_build_forecast_text_no_rain_tmd_radar():
    """
    Test that when there is no rain and the endpoint is tmd-radar,
    the text about omitting timeline and tracking images IS appended.
    """
    result = {
        "max_rain": 0.0,
        "endpoint": "tmd-radar (kkn240)",
        "predictions": [],
        "rain_summary": None,
        "intensity": "ไม่มีฝน",
    }
    text, actual_endpoint, eta_minutes = _build_forecast_text(result)
    
    assert "ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้" in text
    assert actual_endpoint == "tmd-radar (kkn240)"

def test_build_forecast_text_no_rain_open_meteo():
    """
    Test that when there is no rain and the endpoint is Open-Meteo,
    the text about omitting timeline and tracking images is NOT appended.
    """
    result = {
        "max_rain": 0.0,
        "endpoint": "Open-Meteo",
        "predictions": [],
        "rain_summary": None,
        "intensity": "ไม่มีฝน",
    }
    text, actual_endpoint, eta_minutes = _build_forecast_text(result)
    
    assert "ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน 1-2 ชั่วโมงนี้" in text
    assert "(ระบบงดแสดงภาพ Timeline และ Zoom-in Tracking เนื่องจากตรวจไม่พบกลุ่มฝน)" not in text
    assert actual_endpoint == "Open-Meteo"
