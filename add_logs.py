import re

file_path = "backend/app/services/weather_manager.py"
with open(file_path, "r") as f:
    content = f.read()

# Add a log line where user_px and user_py are used in weather_manager.py
# Look for: user_px, user_py = processor.latlng_to_pixel(lat, lng)
target = "user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)"
replacement = """user_px, user_py = processor.latlng_to_pixel(lat, lng, is_loop=False)
                import logging
                logging.info(f"DEBUG_LOCATION: lat={lat}, lng={lng} -> user_px={user_px}, user_py={user_py} (station: {station_code})")"""

if target in content:
    content = content.replace(target, replacement)
    with open(file_path, "w") as f:
        f.write(content)
    print("Logs added successfully.")
else:
    print("Could not find the target string.")
