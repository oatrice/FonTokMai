import os

file_path = "backend/app/services/tmd_radar_processor.py"
with open(file_path, "r") as f:
    content = f.read()

old_str = """        cv2.circle(img, (ux, uy), radius=int(8 * scale), color=(255, 255, 255), thickness=int(2 * scale))
        cv2.drawMarker(img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(12 * scale), int(2 * scale))"""

new_str = """        cv2.circle(img, (ux, uy), radius=int(6 * scale), color=(255, 255, 255), thickness=int(3 * scale))
        cv2.drawMarker(img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(10 * scale), int(3 * scale))"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(file_path, "w") as f:
        f.write(content)
    print("Patched successfully.")
else:
    print("String not found!")
