import re

file_path = "backend/app/services/weather_manager.py"
with open(file_path, "r") as f:
    content = f.read()

target = "user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=use_loop_mapping)"
replacement = """user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=use_loop_mapping)
                import logging
                logging.info(f"DEBUG_LOCATION: lat={lat}, lng={lng} -> user_px={user_px}, user_py={user_py} (station: {station_code}, is_loop={use_loop_mapping})")"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Logs added successfully.")
else:
    print("Could not find the target string.")
