with open('backend/app/services/tmd_radar/nowcast_port.py', 'r') as f:
    src = f.read()

src = src.replace("-> Optional[Dict[str, Any]]:", "-> Optional['RadarPredictionEntity']:")
src = "from app.services.tmd_radar.entities import RadarPredictionEntity\n" + src

with open('backend/app/services/tmd_radar/nowcast_port.py', 'w') as f:
    f.write(src)
