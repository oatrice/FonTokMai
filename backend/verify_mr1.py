import sys
import os
sys.path.append(os.path.abspath('.'))
import cv2
import numpy as np
from app.services.tmd_radar_processor import TMDRadarProcessor

print("1. Testing draw_pin_on_frame...")
# Create a dummy image (e.g. blue-ish background to simulate radar)
img = np.zeros((200, 200, 3), dtype=np.uint8)
img[:] = (255, 0, 0) # Blue background (BGR)

# Draw the pin
TMDRadarProcessor.draw_pin_on_frame(img, 100, 100)

cv2.imwrite("test_pin_output.png", img)
print("-> Saved test_pin_output.png")

print("2. Testing generate_timeline_image...")
predictions = [
    {"time_offset": 0, "dbz": 0.0, "intensity": "ไม่มีฝน", "rain_mm_hr": 0.0, "is_raining": False},
    {"time_offset": 15, "dbz": 30.0, "intensity": "ฝนตกปานกลาง", "rain_mm_hr": 3.0, "is_raining": True},
    {"time_offset": 30, "dbz": 45.0, "intensity": "ฝนตกหนัก", "rain_mm_hr": 15.0, "is_raining": True},
    {"time_offset": 45, "dbz": 20.0, "intensity": "ฝนตกเล็กน้อย", "rain_mm_hr": 1.5, "is_raining": True},
    {"time_offset": 60, "dbz": 0.0, "intensity": "ไม่มีฝน", "rain_mm_hr": 0.0, "is_raining": False},
]

timeline_bytes = TMDRadarProcessor.generate_timeline_image(predictions, location_name="Home")
if timeline_bytes:
    with open("test_timeline_output.png", "wb") as f:
        f.write(timeline_bytes)
    print("-> Saved test_timeline_output.png")
else:
    print("Failed to generate timeline image.")

print("Done! Please open test_pin_output.png and test_timeline_output.png to verify.")
