import asyncio
from datetime import datetime, timezone
import os

from app.services.tmd_radar_processor import TMDRadarProcessor
from app.services.weather_manager import fetch_latest_image_bytes

async def main():
    processor = TMDRadarProcessor("skn240")
    img_bytes = await fetch_latest_image_bytes("skn")
    from PIL import Image
    import io
    import numpy as np
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    curr_frame = np.array(img)
    
    lat = 17.4142
    lng = 104.3943
    user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
    print(f"Generated: {user_px}, {user_py}")
    
    def render_hq_png(target_frame, pin_x, pin_y, time_utc, proc):
        from PIL import Image, ImageFont, ImageDraw
        import io
        from zoneinfo import ZoneInfo
        cf = target_frame.copy()
        proc.draw_pin_on_frame(cf, pin_x, pin_y)
        img_orig = Image.fromarray(cf)
        img_hq = img_orig.resize((int(img_orig.width * 3.0), int(img_orig.height * 3.0)), Image.Resampling.NEAREST)
        
        time_str = time_utc.astimezone(ZoneInfo('Asia/Bangkok')).strftime('%d %b %H:%M')
        try:
            fnt = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 96)
        except:
            fnt = ImageFont.load_default()
                
        draw = ImageDraw.Draw(img_hq, "RGBA")
        left, top, right, bottom = draw.textbbox((0, 0), time_str, font=fnt)
        text_w, text_h = right - left, bottom - top
        
        # We don't need the exact text box for this debug
        
        buffer = io.BytesIO()
        img_hq.save(buffer, format='PNG')
        return buffer.getvalue()
        
    static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, datetime.now(timezone.utc), processor)
    with open("backend/tmp/test_static.png", "wb") as f:
        f.write(static_bytes)
        
    tracking_bytes = await asyncio.to_thread(processor.generate_radar_tracking_image, curr_frame.copy(), user_px, user_py, [])
    with open("backend/tmp/test_tracking.png", "wb") as f:
        f.write(tracking_bytes)

asyncio.run(main())
