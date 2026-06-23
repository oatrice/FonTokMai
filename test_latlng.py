from app.services.tmd_radar_processor import TMDRadarProcessor

processor = TMDRadarProcessor("skn240")
lat, lng = 17.4142, 104.3943
px, py = processor.latlng_to_pixel(lat, lng, is_loop=False)
print(f"Loop=False: lat={lat}, lng={lng} -> px={px}, py={py}")

px, py = processor.latlng_to_pixel(lat, lng, is_loop=True)
print(f"Loop=True : lat={lat}, lng={lng} -> px={px}, py={py}")

print("Center coordinates from config:")
print(f"Center Lat: {processor.config.center_lat}, Lng: {processor.config.center_lng}")

