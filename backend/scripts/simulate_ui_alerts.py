import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env before importing app modules
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Ensure we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.telegram import send_telegram_message, get_radar_inline_keyboard, DEVELOPER_CHAT_IDS

async def simulate_ui():
    if not DEVELOPER_CHAT_IDS or not DEVELOPER_CHAT_IDS[0]:
        print("❌ Error: Please set DEVELOPER_CHAT_IDS in backend/.env")
        return
        
    chat_id = DEVELOPER_CHAT_IDS[0]
    print(f"🚀 Sending test UI alerts to Developer Chat ID: {chat_id}")
    
    # Mock Location (Bangkok)
    lat, lng = 13.75, 100.50
    reply_markup = get_radar_inline_keyboard(lat, lng, is_developer=True)
    
    scenarios = [
        {
            "eta": 0,
            "intensity": "หนัก (Heavy)",
            "duration": 45,
            "title": "⛈️ กรณีฝนตกหนัก ณ ขณะนี้"
        },
        {
            "eta": 15,
            "intensity": "ปานกลาง (Moderate)",
            "duration": 20,
            "title": "🌧️ กรณีฝนปานกลาง กำลังจะมา"
        },
        {
            "eta": 30,
            "intensity": "เบา (Light)",
            "duration": 10,
            "title": "🌦️ กรณีฝนตกเบาๆ กำลังจะมา"
        }
    ]
    
    for s in scenarios:
        print(f"Sending: {s['title']}...")
        if s["eta"] == 0:
            text = "🌧️ ฝนกำลังตกอยู่ที่พิกัดของคุณ ณ ขณะนี้\n"
        else:
            text = f"🌧️ ฝนกำลังเคลื่อนมาทางทิศของคุณ จะเริ่มตกในอีก {s['eta']} นาที\n"
            
        text += f"💧 ความรุนแรง: {s['intensity']}\n"
        text += f"⏱️ คาดว่าจะตกต่อเนื่องประมาณ: {s['duration']} นาที\n"
        
        await send_telegram_message(
            chat_id=chat_id,
            text=f"*{s['title']}*\n\n{text}",
            reply_markup=reply_markup
        )
        await asyncio.sleep(2)
        
    print("✅ All test UI messages sent successfully!")

if __name__ == "__main__":
    asyncio.run(simulate_ui())
