# backend/app/services/tmd_radar/auto_calibration.py

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

class AutoCalibrationService:
    def detect_radar_circle(self, img: np.ndarray) -> Optional[Tuple[int, int, int]]:
        """
        Detects the main radar circle boundary (cx, cy, radius) from an image.
        Uses Hough Circle Detection.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        
        # HoughCircles tuning
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=100,
            param1=50,
            param2=30,
            minRadius=int(min(gray.shape) * 0.25),
            maxRadius=int(min(gray.shape) * 0.49)
        )
        
        if circles is not None:
            circles = np.uint16(np.round(circles))
            # Pick circle closest to center of image
            h, w = gray.shape[:2]
            img_cx, img_cy = w // 2, h // 2
            
            best_circle = None
            min_dist = float('inf')
            
            for c in circles[0, :]:
                cx, cy, r = int(c[0]), int(c[1]), int(c[2])
                dist = (cx - img_cx)**2 + (cy - img_cy)**2
                if dist < min_dist:
                    min_dist = dist
                    best_circle = (cx, cy, r)
            return best_circle
        return None

    def calculate_crops(
        self,
        img_shape: Tuple[int, int, ...],
        circle: Tuple[int, int, int],
        loop_shape: Optional[Tuple[int, int, ...]] = None
    ) -> Dict[str, int]:
        """
        Calculates static_crop and loop_crop bounding boxes from detected radar circle.
        """
        cx, cy, r = circle
        # Static crop enclosing the circle with small padding or exact box
        x_min = max(0, cx - r)
        y_min = max(0, cy - r)
        width = min(img_shape[1] - x_min, r * 2)
        height = min(img_shape[0] - y_min, r * 2)

        crop_info = {
            "static_crop_x": x_min,
            "static_crop_y": y_min,
            "static_crop_width": width,
            "static_crop_height": height
        }

        if loop_shape and img_shape[1] > 0:
            scale_x = loop_shape[1] / float(img_shape[1])
            scale_y = loop_shape[0] / float(img_shape[0])
            crop_info["loop_crop_x"] = int(round(x_min * scale_x))
            crop_info["loop_crop_y"] = int(round(y_min * scale_y))
            crop_info["loop_crop_width"] = int(round(width * scale_x))
            crop_info["loop_crop_height"] = int(round(height * scale_y))
        else:
            crop_info["loop_crop_x"] = x_min
            crop_info["loop_crop_y"] = y_min
            crop_info["loop_crop_width"] = width
            crop_info["loop_crop_height"] = height

        return crop_info

    def generate_config_snippet(
        self,
        code: str,
        name: str,
        static_url: str,
        loop_page_url: str,
        loop_gif_url: str,
        lat: float,
        lng: float,
        radius_km: float,
        crop_info: Dict[str, int]
    ) -> str:
        """
        Formats a python dictionary entry snippet for StationConfig in tmd_radar_config.py
        """
        # Calculate bounding box (approximate 1 deg = 111km)
        deg_offset = radius_km / 111.0
        lat_min = round(lat - deg_offset, 2)
        lat_max = round(lat + deg_offset, 2)
        lng_min = round(lng - deg_offset, 2)
        lng_max = round(lng + deg_offset, 2)

        bbox_const = f"{code.upper()}_BBOX = BoundingBox(lat_max={lat_max}, lng_min={lng_min}, lat_min={lat_min}, lng_max={lng_max})"

        config_entry = f'''    "{code}": StationConfig(
        code="{code}",
        name="{name}",
        static_image_url="{static_url}",
        loop_page_url="{loop_page_url}",
        loop_gif_url="{loop_gif_url}",
        bbox={code.upper()}_BBOX,
        projection_type="azimuthal",
        center_lat={lat},
        center_lng={lng},
        radius_km={radius_km},
        static_crop_x={crop_info["static_crop_x"]},
        static_crop_y={crop_info["static_crop_y"]},
        static_crop_width={crop_info["static_crop_width"]},
        static_crop_height={crop_info["static_crop_height"]},
        loop_crop_x={crop_info["loop_crop_x"]},
        loop_crop_y={crop_info["loop_crop_y"]},
        loop_crop_width={crop_info["loop_crop_width"]},
        loop_crop_height={crop_info["loop_crop_height"]}
    )'''
        return f"{bbox_const}\n\n{config_entry}"

    def draw_crop_preview(
        self,
        img: np.ndarray,
        crop_x: int,
        crop_y: int,
        crop_w: int,
        crop_h: int,
        circle: Optional[Tuple[int, int, int]] = None
    ) -> np.ndarray:
        """
        Draws the active crop rectangle, grid crosshair, and circle boundary onto the image.
        """
        preview = img.copy()
        # Draw Crop Rectangle (cyan)
        cv2.rectangle(preview, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (255, 255, 0), 2)
        
        # Center Crosshair inside crop
        cx = crop_x + crop_w // 2
        cy = crop_y + crop_h // 2
        cv2.line(preview, (cx - 15, cy), (cx + 15, cy), (0, 0, 255), 2)
        cv2.line(preview, (cx, cy - 15), (cx, cy + 15), (0, 0, 255), 2)

        if circle:
            ccx, ccy, r = circle
            cv2.circle(preview, (ccx, ccy), r, (0, 255, 0), 2)

        return preview

    def to_base64_jpeg(self, img: np.ndarray) -> str:
        import base64
        _, buffer = cv2.imencode('.jpg', img)
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

