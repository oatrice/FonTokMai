with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "return RadarPredictionEntity(" in line:
        start_idx = i
        break

for i in range(start_idx, len(lines)):
    if "}" in lines[i] and "tmd_timestamp_bkk" in lines[i-1]:
        lines[i] = lines[i].replace("}", ")")
        break

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.writelines(lines)
