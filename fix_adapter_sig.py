with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

src = src.replace("-> Optional[Dict[str, Any]]:", "-> Optional[RadarPredictionEntity]:")

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(src)
