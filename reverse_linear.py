from app.services.tmd_radar_config import SKN_BBOX

px, py = 693, 566

# x = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min) * 800
lng = (px / 800) * (SKN_BBOX.lng_max - SKN_BBOX.lng_min) + SKN_BBOX.lng_min

# y = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min) * 800
lat = SKN_BBOX.lat_max - (py / 800) * (SKN_BBOX.lat_max - SKN_BBOX.lat_min)

print(f"linear reverse: {lat}, {lng}")
