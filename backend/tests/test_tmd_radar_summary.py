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

@patch("app.services.tmd_radar.tracking.datetime")
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

@patch("app.services.tmd_radar.tracking.datetime")
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

@patch("app.services.tmd_radar.tracking.datetime")
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

@patch("app.services.tmd_radar.tracking.datetime")
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

@patch("app.services.tmd_radar.tracking.datetime")
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
@patch("app.services.tmd_radar.tracking.datetime")
def test_approaching_clouds_warning_with_cache_delay(mock_datetime):
    # Freeze time to 23:00 BKK
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    preds = make_predictions([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    clouds = [{"dbz_now": 35.0, "eta_min": 116.17}] # 116.17 mins from CACHE
    
    # 35 min cache delay
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=35.0, approaching_clouds=clouds)
    
    # Text should say ~55m for no rain (90m - 35m)
    assert "ยังไม่มีแนวโน้มฝนตกในบริเวณของคุณภายใน ~55 นาทีนี้" in summary
    
    # Warning should say ~1 ชม. 21 นาที (116.17m - 35m = 81.17m = 1h 21m)
    assert "หมายเหตุ: ตรวจพบกลุ่มฝน (35 dBZ)" in summary
    assert "1 ชม. 21 นาที" in summary
    assert "00:21 น." in summary

@patch("app.services.tmd_radar.tracking.datetime")
def test_approaching_clouds_warning_skip_if_already_raining(mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    preds = make_predictions([30.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    clouds = [{"dbz_now": 35.0, "eta_min": 116.17}]
    
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0, approaching_clouds=clouds)
    
    # Should say raining now
    assert "ฝนกำลังตกอยู่" in summary
    # Should NOT have warning because it's already raining or rain is arriving sooner than max_time
    assert "หมายเหตุ: ตรวจพบกลุ่มฝน" not in summary


def test_render_rain_summary_suppress_lost_cloud_alert():
    """
    Issue #268: Suppress active rain alert if source cloud is not detected in current frame (all_rain_clusters / clouds).
    """
    # Prediction has a cluster "A" at step 0 (raining now), but approaching_clouds/all_rain_clusters do not have "A"
    preds = [
        {"time_offset": 0, "dbz": 30.0, "intensity": "ฝนปานกลาง", "cluster": "A"},
        {"time_offset": 15, "dbz": 30.0, "intensity": "ฝนปานกลาง", "cluster": "A"},
        {"time_offset": 30, "dbz": 0.0, "intensity": "ไม่มีฝน", "cluster": None},
        {"time_offset": 45, "dbz": 0.0, "intensity": "ไม่มีฝน", "cluster": None},
    ]
    # No clouds present in current frame
    summary = TMDRadarProcessor.render_rain_summary(
        preds,
        time_offset_min=0.0,
        approaching_clouds=[],
        all_rain_clusters=[]
    )
    # Raining alert for cloud A must be suppressed because source cloud A is missing from the frame
    assert "ยังไม่มีแนวโน้มฝนตก" in summary
    assert "ฝนกำลังตกอยู่" not in summary

    # Conversely, if cloud A is actively detected in all_rain_clusters or approaching_clouds, alert is emitted
    summary_with_cloud = TMDRadarProcessor.render_rain_summary(
        preds,
        time_offset_min=0.0,
        approaching_clouds=[{"label": "A", "cx": 100, "cy": 100}],
        all_rain_clusters=[{"label": "A", "cx": 100, "cy": 100}]
    )
    assert "ฝนกำลังตกอยู่" in summary_with_cloud
    assert "[A]" in summary_with_cloud


def test_render_rain_summary_deterministic_with_anchor_time():
    """
    Issue #183: Test that passing anchor_time / anchor timestamp yields completely deterministic clock time without datetime.now() mocking.
    """
    preds = make_predictions([25.0, 25.0, 25.0, 0.0, 0.0, 0.0, 0.0])
    anchor_dt = datetime(2026, 8, 14, 15, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0, anchor_time=anchor_dt)
    assert "ฝนกำลังตกอยู่" in summary
    assert "15:45 น." in summary


