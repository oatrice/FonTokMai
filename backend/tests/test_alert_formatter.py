import pytest
from datetime import datetime, timezone, timedelta
from app.services.alert_formatter import TelegramFormatter, AlertDecision

def test_telegram_formatter_all_clear():
    decision = AlertDecision(
        location_name="home",
        type="all_clear",
        max_rain=0.0,
        result={}
    )
    text = TelegramFormatter.format(decision)
    assert "☀️ สภาพอากาศ ณ พิกัด 'Home' เคลียร์แล้ว" in text
    assert "(ไม่มีแนวโน้มฝนตกในขณะนี้)" in text

def test_telegram_formatter_rain_basic():
    decision = AlertDecision(
        location_name="work",
        type="rain",
        max_rain=15.5,
        result={
            "intensity": "ฝนตกหนัก",
            "duration_minutes": 30,
            "wind_speed_kmh": 20.0,
            "wind_dir_text": "ตะวันออกเฉียงเหนือ",
            "endpoint": "tomorrow",
            "predictions": [{"time": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"), "rain": 15.5}],
            "growth_rate_pct": 10.5
        },
        severity_escalated=True,
        last_max_rain=5.0
    )
    text = TelegramFormatter.format(decision)
    assert "⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*" in text
    assert "(5.0 mm/hr → 15.5 mm/hr)" in text
    assert "ในอีก 14 นาที" in text or "ในอีก 15 นาที" in text
    assert "ตกต่อเนื่อง 30 นาที" in text
    assert "ลม: 20.0 km/h" in text
    assert "กำลังก่อตัวแรงขึ้น (+10.5%/15min)" in text
    assert "Tomorrow.io" in text

