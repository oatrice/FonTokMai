from app.services.tmd_radar_config import SKN_BBOX

lat, lng = 17.1607, 104.1486
bbox = SKN_BBOX

x = int((lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min) * 800)
y = int((bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min) * 800)
print(f"linear: {x}, {y}")
