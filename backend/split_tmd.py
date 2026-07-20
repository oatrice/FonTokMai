import os
import re

source = "app/services/tmd_radar_processor.py"
with open(source, "r") as f:
    content = f.read()

# We want to extract TMDRadarProcessor methods.
# The class starts with 'class TMDRadarProcessor:'
class_start = content.find("class TMDRadarProcessor:")
header = content[:class_start]
body = content[class_start:]

# We can split body into methods using a regex that matches `    def ` or `    async def ` or `    @staticmethod\n    def `
method_pattern = re.compile(r'\n    (?:@staticmethod\n    )?(?:async )?def [a-zA-Z0-9_]+', re.MULTILINE)

matches = list(method_pattern.finditer(body))
methods = {}
for i, match in enumerate(matches):
    start = match.start()
    end = matches[i+1].start() if i + 1 < len(matches) else len(body)
    method_text = body[start:end]
    
    # Extract method name
    name_match = re.search(r'def ([a-zA-Z0-9_]+)', method_text)
    if name_match:
        name = name_match.group(1)
        methods[name] = method_text

# Categorize methods
categories = {
    "clustering": [
        "get_dbz_at_pixel", "_get_dbz_at_pixel_static", "extract_rain_mask", 
        "find_approaching_clouds", "get_all_rain_clusters", "calculate_growth_decay", "_get_max_dbz_in_radius",
        "get_wind_speed_kmh_from_vector", "get_wind_speed_kmh", "get_wind_direction_text_from_vector", "get_wind_direction_text"
    ],
    "tracking": [
        "generate_radar_tracking_image", "render_rain_summary", "generate_timeline_image",
        "draw_pin_on_frame", "_resolve_label_collisions"
    ],
    "multiframe": [
        "calculate_optical_flow", "densify_optical_flow", "calculate_average_optical_flow",
        "generate_flow_debug_images", "generate_multiframe_flow_debug_images", "generate_multiframe_analysis_image",
        "get_flow_vector_at", "extrapolate_rain_at_pixel", "calculate_lagrangian_growth"
    ],
    "cache": [
        "fetch_station_timestamp_utc", "fetch_latest_image_bytes", "fetch_loop_gif_and_extract_frames",
        "fetch_loop_history_bytes", "save_polled_frame", "cleanup_old_frames", "update_radar_cache",
        "decode_static_frame", "parse_html_timestamp"
    ]
}

# Add __init__ and latlng_to_pixel to processor.py
# All others go to their respective mixins

os.makedirs("app/services/tmd_radar", exist_ok=True)

# Generate mixin files
for cat, method_names in categories.items():
    mixin_name = f"TMD{cat.capitalize()}Mixin"
    file_content = header + f"\nclass {mixin_name}:\n"
    
    added_any = False
    for name in method_names:
        if name in methods:
            file_content += methods[name]
            added_any = True
            
    if not added_any:
        file_content += "    pass\n"
        
    with open(f"app/services/tmd_radar/{cat}.py", "w") as f:
        f.write(file_content)

# Generate processor.py
processor_content = header
processor_content += "from .clustering import TMDClusteringMixin\n"
processor_content += "from .tracking import TMDTrackingMixin\n"
processor_content += "from .multiframe import TMDMultiframeMixin\n"
processor_content += "from .cache import TMDCacheMixin\n\n"
processor_content += "class TMDRadarProcessor(TMDCacheMixin, TMDTrackingMixin, TMDMultiframeMixin, TMDClusteringMixin):\n"
processor_content += body[:matches[0].start()] # class definition and docstrings up to first method

for name, text in methods.items():
    found = False
    for cat_methods in categories.values():
        if name in cat_methods:
            found = True
            break
    if not found:
        processor_content += text

with open("app/services/tmd_radar/processor.py", "w") as f:
    f.write(processor_content)
    
with open("app/services/tmd_radar/__init__.py", "w") as f:
    f.write("from .processor import TMDRadarProcessor\n")

# Modify tmd_radar_processor.py to just re-export
with open("app/services/tmd_radar_processor.py", "w") as f:
    f.write("from app.services.tmd_radar.processor import TMDRadarProcessor\n")
    f.write("from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS\n")

print("Done splitting TMDRadarProcessor.")
