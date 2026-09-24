with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

# Replace return { ... } with return RadarPredictionEntity(station_code=station_code, ...)
src = src.replace("return {\n                    \"predictions\":", "return RadarPredictionEntity(\n                    station_code=station_code,\n                    predictions=")

# Close the paren
# We need to find the end of that dictionary.
# "radar_multiframe_bytes\": multiframe_bytes\n                }" -> "radar_multiframe_bytes=multiframe_bytes\n                )"
# "tmd_timestamp_utc": time_utc.isoformat() if time_utc else "",
# "tmd_timestamp_bkk": ... }

src = src.replace("radar_multiframe_bytes\": multiframe_bytes\n                }", "radar_multiframe_bytes=multiframe_bytes\n                )")

import re
# Regex to change dictionary keys to kwargs
def replace_dict_to_kwargs(match):
    content = match.group(0)
    # replace `"key": val` with `key=val`
    content = re.sub(r'"([a-zA-Z0-9_]+)":\s*', r'\1=', content)
    return content

pattern = r'return RadarPredictionEntity\([\s\S]*?radar_multiframe_bytes=multiframe_bytes'
src = re.sub(pattern, replace_dict_to_kwargs, src)

# Also fix tmd_timestamp_utc which is after multiframe_bytes:
src = src.replace('"tmd_timestamp_utc": time_utc.isoformat() if time_utc else "",', 'tmd_timestamp_utc=time_utc.isoformat() if time_utc else "",')
src = src.replace('"tmd_timestamp_bkk": time_bkk.isoformat() if time_bkk else ""\n                }', 'tmd_timestamp_bkk=time_bkk.isoformat() if time_bkk else ""\n                )')

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(src)
