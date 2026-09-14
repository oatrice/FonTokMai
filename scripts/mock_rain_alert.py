#!/usr/bin/env python3
"""
CLI Helper Script สำหรับจำลองส่งการแจ้งเตือนฝนเข้า Telegram เพื่อทดสอบ Presence Ping & TTL Cache
การใช้งาน:
    python3 scripts/mock_rain_alert.py [ชื่อพิกัด] [chat_id] [ความแรงฝน mm/hr]

ตัวอย่าง:
    python3 scripts/mock_rain_alert.py home
    python3 scripts/mock_rain_alert.py d2 6346467495 5.0
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

# Ensure backend path is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.dependencies import get_repo_context
from app.scheduler_tasks import _send_combined_alerts

async def main():
    loc_name = sys.argv[1] if len(sys.argv) > 1 else "home"
    chat_id = int(sys.argv[2]) if len(sys.argv) > 2 else 6346467495
    rain_mm = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5

    print(f"🚀 กำลังจำลองการตรวจพบฝนสำหรับพิกัด [{loc_name}] (Chat ID: {chat_id}, Rain: {rain_mm} mm/hr)...")

    async with get_repo_context() as repo:
        loc = await repo.get_location(chat_id, loc_name)
        if not loc:
            print(f"❌ ไม่พบพิกัด [{loc_name}] ของ chat_id={chat_id}")
            locs = await repo.get_user_locations(chat_id)
            if locs:
                print("📍 พิกัดที่คุณมีในระบบได้แก่:")
                for l in locs:
                    print(f"  - {l.name} (Policy: {l.presence_policy})")
            return

        cached_answer = await repo.get_presence_answer(chat_id, loc.name)
        print(f"📋 สถานะ Cache ปัจจุบัน: {cached_answer or 'ไม่มี (Cache MISS - จะส่งกล่องถามผู้ใช้)'}")
        print(f"⚙️ นโยบายแจ้งเตือนของพิกัด: {loc.presence_policy} (TTL: {loc.presence_answer_ttl_minutes} นาที)")

        simulated_eval_result = [{
            "loc": loc,
            "type": "rain",
            "text": f"🌧️ ตรวจพบกลุ่มฝนใกล้พิกัด [{loc.name}] ความแรง {rain_mm:.1f} mm/hr",
            "max_rain": rain_mm,
            "result": {
                "endpoint": "tomorrow",
                "eta_minutes": 15,
                "duration_minutes": 45
            }
        }]

        sent, errors = await _send_combined_alerts(chat_id, simulated_eval_result, datetime.now(timezone.utc))
        print(f"✅ ส่งแจ้งเตือนจำลองสำเร็จ! (sent={sent}, errors={errors}) ตรวจสอบผลลัพธ์ใน Telegram ได้เลยครับ")

if __name__ == "__main__":
    asyncio.run(main())
