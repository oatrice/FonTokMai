with open("backend/app/services/weather_manager.py", "r") as f:
    content = f.read()

patch = """
import logging
file_handler = logging.FileHandler('/tmp/tmd_radar.log')
file_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(file_handler)
"""
if "FileHandler('/tmp/tmd_radar.log')" not in content:
    content = content.replace("import logging", "import logging" + patch)
    with open("backend/app/services/weather_manager.py", "w") as f:
        f.write(content)
