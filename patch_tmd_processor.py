import re

with open("backend/app/services/tmd_radar_processor.py", "r") as f:
    content = f.read()

start_pattern = "    async def fetch_loop_gif_and_extract_frames("
end_pattern = "    def _get_max_dbz_in_radius("

start_idx = content.find(start_pattern)
end_idx = content.find(end_pattern)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + content[end_idx:]
    with open("backend/app/services/tmd_radar_processor.py", "w") as out_f:
        out_f.write(new_content)
    print("Removed fetch_loop_gif_and_extract_frames successfully!")
else:
    print(f"Could not find patterns! Start: {start_idx}, End: {end_idx}")
