import re

with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

# Replace `"key": value,` with `key=value,`
lines = src.split('\n')
in_entity = False
for i, line in enumerate(lines):
    if "return RadarPredictionEntity(" in line:
        in_entity = True
    elif in_entity and ")" in line and "tmd_timestamp_bkk" in lines[i-1]:
        in_entity = False
    
    if in_entity:
        lines[i] = re.sub(r'"([a-zA-Z0-9_]+)":\s*', r'\1=', line)

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write('\n'.join(lines))
