# backend/app/services/tmd_radar_catalog.py

"""
TMD Radar Station Known Catalog & Initial Seed Data
Provides known TMD radar station presets (Lat/Lng, Names, URLs) for Admin lookup and DB seeding.
"""

KNOWN_TMD_RADAR_PRESETS = [
    {
        "code": "kkn120",
        "name": "Khon Kaen (120km) / ขอนแก่น",
        "static_image_url": "https://weather.tmd.go.th/kkn/kkn120_latest.gif",
        "loop_page_url": "https://weather.tmd.go.th/kknLoop.php",
        "loop_gif_url": "",
        "center_lat": 16.4322,
        "center_lng": 102.8236,
        "radius_km": 120.0,
        "lat_max": 17.53, "lng_min": 101.73, "lat_min": 15.33, "lng_max": 103.93,
        "static_crop_x": 80, "static_crop_y": 40, "static_crop_width": 720, "static_crop_height": 720,
        "loop_crop_x": 80, "loop_crop_y": 40, "loop_crop_width": 600, "loop_crop_height": 600
    },
    {
        "code": "kkn240",
        "name": "Khon Kaen (240km) / ขอนแก่น",
        "static_image_url": "https://weather.tmd.go.th/kkn/kkn240_latest.gif",
        "loop_page_url": "https://weather.tmd.go.th/kknLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/kkn/kknloop.gif",
        "center_lat": 16.4322,
        "center_lng": 102.8236,
        "radius_km": 240.0,
        "lat_max": 18.59, "lng_min": 100.67, "lat_min": 14.27, "lng_max": 104.99,
        "static_crop_x": 80, "static_crop_y": 40, "static_crop_width": 720, "static_crop_height": 720,
        "loop_crop_x": 80, "loop_crop_y": 40, "loop_crop_width": 720, "loop_crop_height": 720
    },
    {
        "code": "skn240",
        "name": "Sakon Nakhon (240km) / สกลนคร",
        "static_image_url": "https://weather.tmd.go.th/skn/skn240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/sknLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/skn/sknloop.gif",
        "center_lat": 17.1607,
        "center_lng": 104.1486,
        "radius_km": 240.0,
        "lat_max": 19.32, "lng_min": 101.95, "lat_min": 15.00, "lng_max": 106.35,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "ubn240",
        "name": "Ubon Ratchathani (240km) / อุบลราชธานี",
        "static_image_url": "https://weather.tmd.go.th/ubn/ubn240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/ubnLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/ubn/ubnloop.gif",
        "center_lat": 15.2447,
        "center_lng": 104.8711,
        "radius_km": 240.0,
        "lat_max": 17.40, "lng_min": 102.71, "lat_min": 13.08, "lng_max": 107.03,
        "static_crop_x": 0, "static_crop_y": 0, "static_crop_width": 800, "static_crop_height": 800,
        "loop_crop_x": 0, "loop_crop_y": 0, "loop_crop_width": 680, "loop_crop_height": 680
    },
    {
        "code": "svp240",
        "name": "Bangkok Suvarnabhumi (240km) / สุวรรณภูมิ",
        "static_image_url": "https://weather.tmd.go.th/svp/svp240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/svpLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/svp/svploop.gif",
        "center_lat": 13.6860,
        "center_lng": 100.7486,
        "radius_km": 240.0,
        "lat_max": 15.85, "lng_min": 98.58, "lat_min": 11.52, "lng_max": 102.91,
        "static_crop_x": 0, "static_crop_y": 0, "static_crop_width": 800, "static_crop_height": 800,
        "loop_crop_x": 0, "loop_crop_y": 0, "loop_crop_width": 680, "loop_crop_height": 680
    },
    {
        "code": "chn",
        "name": "Chainat (240km) / ชัยนาท",
        "static_image_url": "https://weather.tmd.go.th/chn/chn240_latest.gif",
        "loop_page_url": "https://weather.tmd.go.th/chn.php",
        "loop_gif_url": "https://weather.tmd.go.th/chn/chn240_loop.gif",
        "center_lat": 15.1833,
        "center_lng": 100.1167,
        "radius_km": 240.0,
        "lat_max": 17.35, "lng_min": 97.88, "lat_min": 13.02, "lng_max": 102.36,
        "static_crop_x": 0, "static_crop_y": 0, "static_crop_width": 800, "static_crop_height": 800,
        "loop_crop_x": 0, "loop_crop_y": 0, "loop_crop_width": 680, "loop_crop_height": 680
    }
]
