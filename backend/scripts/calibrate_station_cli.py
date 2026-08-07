# backend/scripts/calibrate_station_cli.py

import argparse
import sys
import os
import urllib.request
import cv2
import numpy as np

from app.services.tmd_radar.auto_calibration import AutoCalibrationService

def main():
    parser = argparse.ArgumentParser(description="Auto-calibrate a new TMD radar station using Hough Circle Detection.")
    parser.add_argument("--code", required=True, help="Station code (e.g. cmi240, bkk240)")
    parser.add_argument("--name", required=True, help="Station name (e.g. 'Chiang Mai (240km)')")
    parser.add_argument("--url", required=True, help="URL of the static radar image")
    parser.add_argument("--loop_page_url", default="", help="URL of loop page")
    parser.add_argument("--loop_gif_url", default="", help="Direct URL of loop GIF")
    parser.add_argument("--lat", type=float, required=True, help="Radar station latitude")
    parser.add_argument("--lng", type=float, required=True, help="Radar station longitude")
    parser.add_argument("--radius_km", type=float, default=240.0, help="Radar radius in km (default: 240.0)")
    parser.add_argument("--verify", action="store_true", help="Generate and save verification image overlay")
    parser.add_argument("--output_image", default="calibration_verify.jpg", help="Path to save verification image")

    args = parser.parse_args()

    print(f"Downloading static image from: {args.url} ...")
    try:
        req = urllib.request.Request(args.url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            image_data = resp.read()
    except Exception as e:
        print(f"Failed to download image: {e}", file=sys.stderr)
        sys.exit(1)

    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        print("Failed to decode image.", file=sys.stderr)
        sys.exit(1)

    service = AutoCalibrationService()
    circle = service.detect_radar_circle(img)
    if not circle:
        print("Error: Could not detect radar circle automatically via Hough Circles.", file=sys.stderr)
        sys.exit(1)

    print(f"Detected Radar Circle: center=({circle[0]}, {circle[1]}), radius={circle[2]}px")

    crop_info = service.calculate_crops(img.shape, circle)

    snippet = service.generate_config_snippet(
        code=args.code,
        name=args.name,
        static_url=args.url,
        loop_page_url=args.loop_page_url or f"https://weather.tmd.go.th/{args.code[:3]}Loop.php",
        loop_gif_url=args.loop_gif_url,
        lat=args.lat,
        lng=args.lng,
        radius_km=args.radius_km,
        crop_info=crop_info
    )

    print("\n" + "="*60)
    print("CALIBRATED CONFIGURATION SNIPPET:")
    print("="*60)
    print(snippet)
    print("="*60 + "\n")

    if args.verify:
        overlay = service.draw_verification_overlay(img, circle, (circle[0], circle[1]))
        cv2.imwrite(args.output_image, overlay)
        print(f"Verification overlay image saved to: {args.output_image}")

if __name__ == "__main__":
    main()
