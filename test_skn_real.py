from app.services.tmd_radar_processor import TMDRadarProcessor

lat, lng = 17.1607, 104.1486

proc_kkn = TMDRadarProcessor("kkn240")
px, py = proc_kkn.latlng_to_pixel(lat, lng, is_loop=False)
print(f"kkn240: {px}, {py}")

proc_skn = TMDRadarProcessor("skn240")
px, py = proc_skn.latlng_to_pixel(lat, lng, is_loop=False)
print(f"skn240: {px}, {py}")

