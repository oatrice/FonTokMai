import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.tmd_radar_config import STATIONS

def zoom_out_full_radar():
    img_path = "/tmp/ryg_latest.jpg"
    raw_bgr = cv2.imread(img_path)
    st = STATIONS["ryg"]

    crop_x, crop_y, crop_w, crop_h = st.static_crop_x, st.static_crop_y, st.static_crop_width, st.static_crop_height
    cropped_bgr = raw_bgr[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w].copy()
    cropped_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)

    hsv_full = cv2.cvtColor(cropped_rgb, cv2.COLOR_RGB2HSV)

    # Sea mask
    diff_sea = np.abs(cropped_rgb.astype(np.int16) - np.array([128, 192, 254], dtype=np.int16))
    is_sea = np.all(diff_sea <= 18, axis=2)

    # Pure green rain
    green_rain = cv2.inRange(hsv_full, np.array([55, 150, 80], dtype=np.uint8), np.array([65, 255, 255], dtype=np.uint8))
    green_rain[is_sea] = 0

    # Morphological dilation
    kernel_d = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    dilated = cv2.dilate(green_rain, kernel_d)
    dilated[is_sea] = 0

    cnts, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Total contours found in full radar scan: {len(cnts)}")

    # Scale 2x for visualization clarity
    scale = 2
    scaled_bgr = cv2.resize(cropped_bgr, (crop_w * scale, crop_h * scale), interpolation=cv2.INTER_NEAREST)
    scaled_rgb = cv2.cvtColor(scaled_bgr, cv2.COLOR_BGR2RGB)
    scaled_h, scaled_w = scaled_rgb.shape[:2]

    # Function to draw 8x8 Grid overlay
    def draw_8x8_grid(img, highlight_cell=("D", 1)):
        grid_img = img.copy()
        cw = scaled_w / 8.0
        ch = scaled_h / 8.0
        cols = ["A", "B", "C", "D", "E", "F", "G", "H"]
        rows = [1, 2, 3, 4, 5, 6, 7, 8]

        # Draw grid lines
        for c in range(1, 8):
            x = int(c * cw)
            cv2.line(grid_img, (x, 0), (x, scaled_h), (255, 255, 255), 1)
        for r in range(1, 8):
            y = int(r * ch)
            cv2.line(grid_img, (0, y), (scaled_w, y), (255, 255, 255), 1)

        # Highlight specific cell (e.g. D1 -> Row index 3, Col index 0)
        # Note: D1 in standard naming convention: Col D (index 3), Row 1 (index 0) or Row D (index 3), Col 1 (index 0)
        # In earlier steps: d1_x1, d1_x2 = 0, crop_w*(1/8) [Col 1 / A], d1_y1, d1_y2 = crop_h*(3/8)..crop_h*(4/8) [Row 4 / D]
        # So cell D1 is Row 4 (D), Col 1 (1).
        cell_r = 3  # D (0-indexed 3)
        cell_c = 0  # 1 (0-indexed 0)

        gx1, gy1 = int(cell_c * cw), int(cell_r * ch)
        gx2, gy2 = int((cell_c + 1) * cw), int((cell_r + 1) * ch)

        # Highlight rectangle
        cv2.rectangle(grid_img, (gx1, gy1), (gx2, gy2), (0, 255, 255), 3)
        cv2.putText(grid_img, "D1", (gx1 + 5, gy1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Draw labels
        for r in range(8):
            for c in range(8):
                cell_name = f"{cols[r]}{rows[c]}"
                lx = int(c * cw) + 5
                ly = int(r * ch) + 15
                if cell_name != "D1":
                    cv2.putText(grid_img, cell_name, (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        return grid_img

    # Panel 1: Raw with 8x8 Grid
    p1 = draw_8x8_grid(scaled_bgr)
    cv2.putText(p1, "P1: Full Radar with 8x8 Grid (D1 Highlighted)", (10, scaled_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Panel 2: Rain Mask
    mask_sc = cv2.resize(green_rain, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
    p2 = scaled_bgr.copy()
    p2[mask_sc > 0] = [0, 255, 0]
    p2 = draw_8x8_grid(p2)
    cv2.putText(p2, f"P2: Rain Mask ({np.count_nonzero(green_rain)}px)", (10, scaled_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Panel 3: Neon Magenta Contours over full radar
    pil_roi = Image.fromarray(scaled_rgb).convert("RGBA")
    layer = Image.new("RGBA", pil_roi.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    for ctr in cnts:
        scaled_pts = [(int(p[0][0] * scale), int(p[0][1] * scale)) for p in ctr]
        if len(scaled_pts) >= 3:
            d.polygon(scaled_pts, fill=(255, 0, 255, 70))
            d.line(scaled_pts + [scaled_pts[0]], fill=(255, 0, 255, 255), width=4)

    glow = layer.copy().filter(ImageFilter.GaussianBlur(radius=3))
    result = Image.alpha_composite(pil_roi, glow)
    result = Image.alpha_composite(result, layer)
    p3_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGBA2BGR)

    # Draw bounding boxes & centroids
    for i, ctr in enumerate(cnts):
        x, y, w, h = cv2.boundingRect(ctr)
        M = cv2.moments(ctr)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"] * scale)
            cy = int(M["m01"] / M["m00"] * scale)
            cv2.rectangle(p3_bgr, (x*scale, y*scale), ((x+w)*scale, (y+h)*scale), (0, 255, 255), 1)
            cv2.circle(p3_bgr, (cx, cy), 4, (0, 0, 255), -1)

    p3 = draw_8x8_grid(p3_bgr)
    cv2.putText(p3, "P3: Neon Magenta Contours (Full Radar)", (10, scaled_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)

    composite = np.hstack([p1, p2, p3])
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_neon_output.png")
    cv2.imwrite(out_path, composite)
    print(f"\n✅ Saved: {out_path}")
    print("👉 open " + out_path)

if __name__ == "__main__":
    zoom_out_full_radar()
