import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.tmd_radar_processor import TMDRadarProcessor

def make_predictions(dbz_list):
    """Helper to mock predictions list matching what WeatherManager creates."""
    preds = []
    for i, d in enumerate(dbz_list):
        preds.append({
            "time_offset": i * 15,
            "dbz": float(d),
            "intensity": "ฝนปานกลาง" if d >= 15 else "ไม่มีฝน"
        })
    return preds

def test_render_rain_summary_no_rain():
    # predictions list with no dbz >= 15.0
    preds = make_predictions([0.0, 5.0, 10.0, 5.0, 0.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=15.0)
    assert "ยังไม่มีแนวโน้มฝนตก" in summary
    assert "~1 ชม. 15 นาที" in summary # max_time (90m) - time_offset_min (15m) = 75m = ~1 ชม. 15 นาที

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_raining_now_stops(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Raining now (Step 0 >= 15), stops at Step 3 (+45m)
    preds = make_predictions([25.0, 25.0, 25.0, 0.0, 0.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0)
    
    # Expect stop in 45m (which is 23:45)
    assert "ฝนกำลังตกอยู่" in summary
    assert "ฝนปานกลาง" in summary
    assert "จะหยุดตกในอีก ~45 นาที" in summary
    assert "23:45 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_raining_now_continuous(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Raining now, never stops (all >= 15)
    preds = make_predictions([35.0, 35.0, 35.0, 35.0, 35.0, 35.0, 35.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0)
    
    # Expect continuous till max prediction time (90m = 00:30)
    assert "ฝนกำลังตกอยู่" in summary
    assert "ฝนหนัก" in summary
    assert "จะตกต่อเนื่องถึงอย่างน้อย ~1 ชม. 30 นาที" in summary
    assert "00:30 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_incoming_rain(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # No rain now (Step 0-2 = 0), Rain starts at Step 3 (+45m), stops at Step 6 (+90m)
    preds = make_predictions([0.0, 0.0, 0.0, 25.0, 25.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0)
    
    # It should say rain is coming in 45m (25 dBZ) and continues for 30m
    assert "ฝนกำลังจะมาใน ~45 นาที" in summary
    assert "25 dBZ" in summary
    assert "จะตกต่อเนื่องประมาณ 30 นาที" in summary
    assert "00:15 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_incoming_rain_cache_delayed_raining_now(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # The cache says: no rain now (Step 0 = 0), rain starts at Step 1 (+15m), stops at Step 3 (+45m)
    # BUT time_offset_min = 15m. So Step 1 is ACTUALLY right now (0m). Step 3 is 30m away.
    preds = make_predictions([0.0, 25.0, 25.0, 0.0, 0.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=15.0)
    
    # Because of delay, it should say raining NOW!
    assert "ฝนกำลังตกอยู่" in summary
    assert "จะหยุดตกในอีก ~30 นาที" in summary
    assert "23:30 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_with_heavy_spike(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Rain starts at Step 1 (+15m) with 20 dBZ (ปานกลาง)
    # At Step 3 (+45m), it spikes to 45 dBZ (หนัก)
    preds = make_predictions([0.0, 20.0, 20.0, 45.0, 45.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0)
    
    assert "ฝนกำลังจะมาใน ~15 นาที" in summary
    assert "20 dBZ" in summary
    assert "ตกหนักขึ้นใน ~45 นาที" in summary
    assert "45 dBZ" in summary
    assert "ตกต่อเนื่องประมาณ 60 นาที" in summary # 75m - 15m = 60m
    assert "00:15 น." in summary

def test_approaching_clouds_warning():
    preds = make_predictions([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    clouds = [{"dbz_now": 35.0, "eta_min": 116.17}]
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0, approaching_clouds=clouds)
    assert "ยังไม่มีแนวโน้มฝนตก" in summary
    assert "หมายเหตุ: ตรวจพบกลุ่มฝน (35 dBZ)" in summary
    assert "1 ชม. 56 นาที" in summary
