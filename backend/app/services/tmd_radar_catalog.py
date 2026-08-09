# backend/app/services/tmd_radar_catalog.py

"""
TMD Radar Station Known Catalog & Initial Seed Data
Provides known TMD radar station presets (Lat/Lng, Names, URLs) for Admin lookup and DB seeding.
"""

KNOWN_TMD_RADAR_PRESETS = [
    {
        "code": "svp240",
        "name": "Bangkok Suvarnabhumi (240km) / สุวรรณภูมิ",
        "static_image_url": "https://weather.tmd.go.th/svp/svp240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/svpLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/svp/svp240_HQ_Loop.gif",
        "center_lat": 13.6860,
        "center_lng": 100.7486,
        "radius_km": 240.0,
        "lat_max": 15.85, "lng_min": 98.59, "lat_min": 11.53, "lng_max": 102.91,
        "static_crop_x": 267, "static_crop_y": 197, "static_crop_width": 402, "static_crop_height": 402,
        "loop_crop_x": 267, "loop_crop_y": 197, "loop_crop_width": 402, "loop_crop_height": 402
    },
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
        "code": "ntp240",
        "name": "Nonthaburi / Don Mueang (240km) / นนทบุรี",
        "static_image_url": "https://weather.tmd.go.th/ntp/ntp240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/ntpLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/ntp/ntploop.gif",
        "center_lat": 13.8700,
        "center_lng": 100.5300,
        "radius_km": 240.0,
        "lat_max": 16.03, "lng_min": 98.37, "lat_min": 11.71, "lng_max": 102.69,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "cmi240",
        "name": "Chiang Mai (240km) / เชียงใหม่",
        "static_image_url": "https://weather.tmd.go.th/cmi/cmi240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/cmiLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/cmi/cmiloop.gif",
        "center_lat": 18.7700,
        "center_lng": 98.9700,
        "radius_km": 240.0,
        "lat_max": 20.93, "lng_min": 96.81, "lat_min": 16.61, "lng_max": 101.13,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "phs240",
        "name": "Phitsanulok (240km) / พิษณุโลก",
        "static_image_url": "https://weather.tmd.go.th/phs/phs240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/phsLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/phs/phsloop.gif",
        "center_lat": 16.7800,
        "center_lng": 100.2700,
        "radius_km": 240.0,
        "lat_max": 18.94, "lng_min": 98.11, "lat_min": 14.62, "lng_max": 102.43,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "ubn240",
        "name": "Ubon Ratchathani (240km) / อุบลราชธานี",
        "static_image_url": "https://weather.tmd.go.th/ubn/ubn240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/ubnLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/ubn/ubnloop.gif",
        "center_lat": 15.2500,
        "center_lng": 104.8800,
        "radius_km": 240.0,
        "lat_max": 17.41, "lng_min": 102.72, "lat_min": 13.09, "lng_max": 107.04,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "srt240",
        "name": "Surat Thani (240km) / สุราษฎร์ธานี",
        "static_image_url": "https://weather.tmd.go.th/srt/srt240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/srtLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/srt/srtloop.gif",
        "center_lat": 9.1300,
        "center_lng": 99.1800,
        "radius_km": 240.0,
        "lat_max": 11.29, "lng_min": 97.02, "lat_min": 6.97, "lng_max": 101.34,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "pkt240",
        "name": "Phuket (240km) / ภูเก็ต",
        "static_image_url": "https://weather.tmd.go.th/pkt/pkt240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/pktLoop.php",
        "loop_gif_url": "https://weather.tmd.go.th/pkt/pktloop.gif",
        "center_lat": 7.8800,
        "center_lng": 98.3200,
        "radius_km": 240.0,
        "lat_max": 10.04, "lng_min": 96.16, "lat_min": 5.72, "lng_max": 100.48,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    }
]
