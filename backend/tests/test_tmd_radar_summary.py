import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.services.tmd_radar_processor import TMDRadarProcessor

# Helper to create predictions
def make_predictions(dbz_list):
    predictions = []
    base_time = datetime.now(timezone.utc)
    for i, dbz in enumerate(dbz_list):
        predictions.append({
            "time": (base_time + timedelta(minutes=i * 15)).isoformat(),
            "time_offset": float(i * 15),
            "dbz": float(dbz),
            "rain": 0.0,
            "cluster": "A" if dbz >= 15.0 else None,
            "src_x": 0,
            "src_y": 0
        })
    return predictions

@pytest.fixture
def fixed_bkk_time():
    # Freeze current time to 23:00 BKK time (16:00 UTC)
    # timedelta(hours=7) is BKK timezone offset
    bkk_timezone = timezone(timedelta(hours=7))
    frozen_bkk_now = datetime(2026, 6, 27, 23, 0, 0, tzinfo=bkk_timezone)
    
    with patch("datetime.datetime") as mock_datetime:
        # datetime.now(tz) should return frozen_bkk_now in BKK timezone
        # Since datetime is a built-in, we mock it carefully or mock the datetime.now call
        mock_datetime.now.return_value = frozen_bkk_now
        yield frozen_bkk_now

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
    assert "ขณะนี้มีฝนตกในบริเวณของคุณ" in summary
    assert "ฝนปานกลาง" in summary
    assert "จะหยุดตกในอีก ~45 นาที" in summary
    assert "23:45 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_raining_now_continuous(mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Raining now, never stops (all >= 15)
    preds = make_predictions([35.0, 35.0, 35.0, 35.0, 35.0, 35.0, 35.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=0.0)
    
    # Expect continuous till max prediction time (90m = 00:30)
    assert "ฝนหนัก" in summary
    assert "จะตกต่อเนื่องถึงอย่างน้อย ~1 ชม. 30 นาที" in summary
    assert "00:30 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_incoming_rain(mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Rain starts at Step 4 (+60m), stops at Step 6 (+90m)
    # Cache delay is 15 minutes.
    # So rain starts at 60m from frame. Relative to now, it starts in 60 - 15 = 45m.
    # It stops at 90m from frame. Relative to now, it stops in 90 - 15 = 75m (00:15).
    # Duration: 30 minutes.
    preds = make_predictions([0.0, 0.0, 0.0, 0.0, 25.0, 25.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=15.0)
    
    assert "ฝนกำลังจะมาใน ~45 นาที" in summary
    assert "จะตกต่อเนื่องประมาณ 30 นาที" in summary
    assert "00:15 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_incoming_rain_cache_delayed_raining_now(mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Rain starts at Step 1 (+15m), stops at Step 3 (+45m)
    # Cache delay is 15 minutes.
    # adj_start = 15 - 15 = 0 -> adjusted to "currently raining".
    # stop_time = 45m. Relative to now, stops in 45 - 15 = 30m (23:30).
    preds = make_predictions([0.0, 25.0, 25.0, 0.0, 0.0, 0.0, 0.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=15.0)
    
    assert "ฝนกำลังตกอยู่" in summary
    assert "จะหยุดตกในอีก ~30 นาที" in summary
    assert "23:30 น." in summary

@patch("app.services.tmd_radar_processor.datetime")
def test_render_rain_summary_with_heavy_spike(mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 6, 27, 23, 0, 0, tzinfo=timezone(timedelta(hours=7)))
    
    # Rain starts at Step 2 (+30m, 20 dBZ)
    # Gets heavier at Step 4 (+60m, 40 dBZ)
    # Cache delay is 15 minutes.
    # adj_start = 30 - 15 = 15m.
    # Heavy spike is at 60m (adjusted: 60 - 15 = 45m).
    # Never stops.
    preds = make_predictions([0.0, 0.0, 20.0, 25.0, 40.0, 40.0, 40.0])
    summary = TMDRadarProcessor.render_rain_summary(preds, time_offset_min=15.0)
    
    assert "ฝนกำลังจะมาใน ~15 นาที" in summary
    assert "จะตกหนักขึ้นใน ~45 นาที" in summary
    assert "ฝนหนัก" in summary
    assert "จะตกต่อเนื่องอย่างน้อย 60 นาที" in summary
    assert "00:15 น." in summary
