lat = 17.41
lng = 104.78
lat_max = 19.32
lng_min = 101.95
lat_min = 15.00
lng_max = 106.35
crop_width = 620
crop_height = 620
crop_x = 61
crop_y = 24

x_pct = (lng - lng_min) / (lng_max - lng_min)
y_pct = (lat_max - lat) / (lat_max - lat_min)

x = int(x_pct * crop_width) + crop_x
y = int(y_pct * crop_height) + crop_y

print(f"X={x}, Y={y}")
