import cv2
import numpy as np
from typing import List, Tuple, Optional
from app.services.tmd_radar_config import STATIONS, DBZ_COLOR_MAPPING, IGNORED_COLORS

class TMDRadarProcessor:
    def __init__(self, station_code: str):
        self.station_code = station_code
        if station_code not in STATIONS:
            raise ValueError(f"Unknown station code: {station_code}")
        self.config = STATIONS[station_code]

    def latlng_to_pixel(self, lat: float, lng: float) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box."""
        bbox = self.config.bbox
        
        if not (bbox.lat_min <= lat <= bbox.lat_max and bbox.lng_min <= lng <= bbox.lng_max):
            return None, None
            
        # Linear interpolation
        x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
        y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)
        
        # Crop offsets
        x = int(x_pct * self.config.crop_width) + self.config.crop_x
        y = int(y_pct * self.config.crop_height) + self.config.crop_y
        
        return x, y

    def get_dbz_at_pixel(self, img: np.ndarray, x: int, y: int) -> float:
        """Reads the color at (x,y) and returns the corresponding dBZ value."""
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return 0.0
            
        # OpenCV defaults to BGR, but assuming img is RGB for this function or passed as RGB.
        # Let's extract pixel.
        pixel = img[y, x]
        # Ensure it's a tuple for dict lookup
        if len(pixel) >= 3:
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        else:
            return 0.0
            
        color_tuple = (r, g, b)
        
        # Check ignored
        if color_tuple in IGNORED_COLORS:
            return 0.0
            
        # Exact match
        if color_tuple in DBZ_COLOR_MAPPING:
            return DBZ_COLOR_MAPPING[color_tuple]
            
        # If no exact match, we could do nearest neighbor color matching here.
        # For MVP, we return 0.0 if not matched exactly.
        return 0.0

    def calculate_optical_flow(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Calculates dense optical flow using Farneback algorithm between the last two frames.
        frames: List of image arrays in RGB or Grayscale.
        Returns: Flow vector array of shape (H, W, 2)
        """
        if len(frames) < 2:
            raise ValueError("At least 2 frames required for optical flow")
            
        prev_img = frames[-2]
        curr_img = frames[-1]
        
        # Convert to Grayscale if they are color
        if len(prev_img.shape) == 3:
            prev_gray = cv2.cvtColor(prev_img, cv2.COLOR_RGB2GRAY)
        else:
            prev_gray = prev_img
            
        if len(curr_img.shape) == 3:
            curr_gray = cv2.cvtColor(curr_img, cv2.COLOR_RGB2GRAY)
        else:
            curr_gray = curr_img
            
        # Calculate dense optical flow by Farneback method
        # flow[y, x, 0] = dx
        # flow[y, x, 1] = dy
        flow = cv2.calcOpticalFlowFarneback(
            prev=prev_gray,
            next=curr_gray,
            flow=None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        return flow
        
    def get_flow_vector_at(self, flow: np.ndarray, x: int, y: int) -> Tuple[float, float]:
        """Returns the (dx, dy) velocity vector from optical flow array at given pixel."""
        if x < 0 or x >= flow.shape[1] or y < 0 or y >= flow.shape[0]:
            return 0.0, 0.0
            
        vx = float(flow[y, x, 0])
        vy = float(flow[y, x, 1])
        return vx, vy

    def calculate_growth_decay(self, prev_img: np.ndarray, curr_img: np.ndarray, x: int, y: int, radius: int = 10) -> float:
        """
        Calculates the growth or decay percentage of a rain cell around (x, y).
        Positive = Growth (Formation / Intensification)
        Negative = Decay (Dissipation / Weakening)
        
        It compares the sum of dBZ values in the region between the two frames.
        """
        prev_sum = 0.0
        curr_sum = 0.0
        count = 0
        
        # Look at a bounding box around (x,y)
        x_start = max(0, x - radius)
        x_end = min(curr_img.shape[1], x + radius)
        y_start = max(0, y - radius)
        y_end = min(curr_img.shape[0], y + radius)
        
        for iy in range(y_start, y_end):
            for ix in range(x_start, x_end):
                dbz_prev = self.get_dbz_at_pixel(prev_img, ix, iy)
                dbz_curr = self.get_dbz_at_pixel(curr_img, ix, iy)
                prev_sum += dbz_prev
                curr_sum += dbz_curr
                count += 1
                
        if count == 0:
            return 0.0
            
        if prev_sum == 0 and curr_sum == 0:
            return 0.0
        elif prev_sum == 0 and curr_sum > 0:
            return 100.0 # Formed from nothing
        elif prev_sum > 0 and curr_sum == 0:
            return -100.0 # Dissipated completely
            
        percent_change = ((curr_sum - prev_sum) / prev_sum) * 100.0
        return percent_change

    async def fetch_latest_image_bytes(self) -> Optional[bytes]:
        """Fetches the latest static radar image (Polling method)."""
        import httpx
        url = self.config.static_image_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
        except Exception:
            pass
        return None

    async def fetch_loop_history_bytes(self) -> List[bytes]:
        """
        Fetches the history of images from the loop page.
        This is a stub. Real implementation requires scraping the loop.php HTML.
        For MVP, we just try to fetch the latest static image as history.
        """
        # TODO: Implement actual HTML scraping of self.config.loop_page_url
        # For now, return an empty list to fallback to polling
        return []

