import re

with open('backend/app/services/tmd_radar/adapter.py', 'r') as f:
    src = f.read()

src = src.replace("from app.services.tmd_radar.processor import TMDRadarProcessor", 
                  "from app.services.tmd_radar.processor import TMDRadarProcessor\nfrom app.services.tmd_radar.renderer_impl import DefaultRadarRenderer")

# In predict():
# We need to find `processor = TMDRadarProcessor(station_code)` and add `renderer = DefaultRadarRenderer(processor)`
src = src.replace("processor = TMDRadarProcessor(station_code)", 
                  "processor = TMDRadarProcessor(station_code)\n        renderer = DefaultRadarRenderer(processor)")

src = src.replace("processor.generate_radar_tracking_image(", "renderer.generate_radar_tracking_image(")
src = src.replace("processor.generate_timeline_image(", "renderer.generate_timeline_image(")
src = src.replace("processor.generate_multiframe_analysis_image(", "renderer.generate_multiframe_analysis_image(")

# Also we need to use RadarPredictionEntity
src = src.replace("from app.services.tmd_radar.nowcast_port import NowcastPort", 
                  "from app.services.tmd_radar.nowcast_port import NowcastPort\nfrom app.services.tmd_radar.entities import RadarPredictionEntity, RainPrediction")

with open('backend/app/services/tmd_radar/adapter.py', 'w') as f:
    f.write(src)
