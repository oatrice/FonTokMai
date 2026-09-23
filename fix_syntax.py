import re

with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

# Replace all `"key":` with `key=` inside the return RadarPredictionEntity block
start_idx = src.find("return RadarPredictionEntity(")
end_idx = src.find("}", start_idx)

if start_idx != -1 and end_idx != -1:
    block = src[start_idx:end_idx]
    block = re.sub(r'"([a-zA-Z0-9_]+)":\s*', r'\1=', block)
    src = src[:start_idx] + block + ")" + src[end_idx+1:]

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(src)
