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
        "static_crop_x": 71, "static_crop_y": 29, "static_crop_width": 724, "static_crop_height": 724,
        "loop_crop_x": 71, "loop_crop_y": 29, "loop_crop_width": 724, "loop_crop_height": 724
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
        "loop_gif_url": "https://weather.tmd.go.th/chn/chnloop.gif",
        "center_lat": 15.158238,
        "center_lng": 100.191207,
        "radius_km": 240.0,
        "lat_max": 17.35, "lng_min": 97.88, "lat_min": 13.02, "lng_max": 102.36,
        "static_crop_x": 0, "static_crop_y": 0, "static_crop_width": 800, "static_crop_height": 800,
        "loop_crop_x": 0, "loop_crop_y": 0, "loop_crop_width": 680, "loop_crop_height": 680
    },
    {
        "code": "ryg",
        "name": "Rayong (240km) / ระยอง",
        "static_image_url": "https://weather.tmd.go.th/ryg/ryg240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/rygloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/ryg/rygloop.gif",
        "center_lat": 12.6814,
        "center_lng": 101.2817,
        "radius_km": 240.0,
        "lat_max": 14.84, "lng_min": 99.12, "lat_min": 10.52, "lng_max": 103.44,
        "static_crop_x": 0, "static_crop_y": 0, "static_crop_width": 800, "static_crop_height": 800,
        "loop_crop_x": 0, "loop_crop_y": 0, "loop_crop_width": 680, "loop_crop_height": 680
    },
    {
        "code": "phs",
        "name": "Phitsanulok (240km) / พิษณุโลก",
        "static_image_url": "https://weather.tmd.go.th/phs/phs240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/phsloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/phs/phsloop.gif",
        "center_lat": 16.7828,
        "center_lng": 100.2786,
        "radius_km": 240.0,
        "lat_max": 18.94, "lng_min": 98.11, "lat_min": 14.62, "lng_max": 102.43,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "cmp",
        "name": "Chumphon (240km) / ชุมพร",
        "static_image_url": "https://weather.tmd.go.th/cmp/cmp240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/cmploop.php",
        "loop_gif_url": "https://weather.tmd.go.th/cmp/cmpLoop.gif",
        "center_lat": 10.4931,
        "center_lng": 99.1800,
        "radius_km": 240.0,
        "lat_max": 12.66, "lng_min": 97.02, "lat_min": 8.33, "lng_max": 101.34,
        "static_crop_x": 8, "static_crop_y": 13, "static_crop_width": 750, "static_crop_height": 750,
        "loop_crop_x": 8, "loop_crop_y": 13, "loop_crop_width": 750, "loop_crop_height": 750
    },
    {
        "code": "tak",
        "name": "Doi Muser, Tak Province (240km) / ตาก (ดอยมูเซอ)",
        "static_image_url": "https://weather.tmd.go.th/tak/tak240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/takloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/tak/takloop.gif",
        "center_lat": 16.750,
        "center_lng": 98.930,
        "radius_km": 240.0,
        "lat_max": 18.65, "lng_min": 97.01, "lat_min": 14.32, "lng_max": 101.33,
        "static_crop_x": 72, "static_crop_y": 28, "static_crop_width": 728, "static_crop_height": 728,
        "loop_crop_x": 72, "loop_crop_y": 28, "loop_crop_width": 728, "loop_crop_height": 728
    },
    {
        "code": "cri",
        "name": "Chiang Rai (240km) / เชียงราย",
        "static_image_url": "https://weather.tmd.go.th/cri/cri240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/criloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/cri/criloop.gif",
        "center_lat": 19.9609,
        "center_lng": 99.8824,
        "radius_km": 240.0,
        "lat_max": 22.12, "lng_min": 97.72, "lat_min": 17.80, "lng_max": 102.04,
        "static_crop_x": 71, "static_crop_y": 29, "static_crop_width": 724, "static_crop_height": 724,
        "loop_crop_x": 71, "loop_crop_y": 29, "loop_crop_width": 724, "loop_crop_height": 724
    },
    {
        "code": "srt",
        "name": "Surat Thani (240km) / สุราษฎร์ธานี",
        "static_image_url": "https://weather.tmd.go.th/srt/srt240_latest.png",
        "loop_page_url": "https://weather.tmd.go.th/srtloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/srt/srtloop.gif",
        "center_lat": 9.1333,
        "center_lng": 99.3333,
        "radius_km": 240.0,
        "lat_max": 11.29, "lng_min": 97.17, "lat_min": 6.97, "lng_max": 101.49,
        "static_crop_x": 71, "static_crop_y": 29, "static_crop_width": 724, "static_crop_height": 724,
        "loop_crop_x": 71, "loop_crop_y": 29, "loop_crop_width": 724, "loop_crop_height": 724
    },
    {
        "code": "hyi",
        "name": "Hat Yai (240km) / หาดใหญ่",
        "static_image_url": "https://weather.tmd.go.th/hyi/hyi240_latest.jpg",
        "loop_page_url": "https://weather.tmd.go.th/hyiloop.php",
        "loop_gif_url": "https://weather.tmd.go.th/hyi/hyiloop.gif",
        "center_lat": 6.9248,
        "center_lng": 100.4385,
        "radius_km": 240.0,
        "lat_max": 9.08, "lng_min": 98.28, "lat_min": 4.76, "lng_max": 102.60,
        "static_crop_x": 71, "static_crop_y": 29, "static_crop_width": 724, "static_crop_height": 724,
        "loop_crop_x": 71, "loop_crop_y": 29, "loop_crop_width": 724, "loop_crop_height": 724
    }
]
