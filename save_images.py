import re

file_path = "backend/app/services/weather_manager.py"
with open(file_path, "r") as f:
    content = f.read()

target = "static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, now_utc, processor)"
replacement = """static_bytes = await asyncio.to_thread(render_hq_png, curr_frame.copy(), user_px, user_py, now_utc, processor)
                    with open("backend/tmp/debug_static.png", "wb") as f:
                        f.write(static_bytes)"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Static save added.")

target2 = "tracking_bytes = await asyncio.to_thread(processor.generate_radar_tracking_image, curr_frame.copy(), user_px, user_py, clouds)"
replacement2 = """tracking_bytes = await asyncio.to_thread(processor.generate_radar_tracking_image, curr_frame.copy(), user_px, user_py, clouds)
                    with open("backend/tmp/debug_tracking.png", "wb") as f:
                        f.write(tracking_bytes)"""

if target2 in content:
    content = content.replace(target2, replacement2)
    with open(file_path, "w") as f:
        f.write(content)
    print("Tracking save added.")

