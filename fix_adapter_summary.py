with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

src = src.replace("processor.render_rain_summary(", "renderer.render_rain_summary(")

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(src)
