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
        import os
        self.storage_dir = os.path.join(os.getcwd(), "backend", "tmp")

    def latlng_to_pixel(self, lat: float, lng: float, is_loop: bool = True, projection: str = None) -> Tuple[Optional[int], Optional[int]]:
        """Converts geographical coordinates to image pixel coordinates based on bounding box."""
        bbox = self.config.bbox
        if lat > bbox.lat_max or lat < bbox.lat_min or lng < bbox.lng_min or lng > bbox.lng_max:
            return None, None
            
        # Use config's projection if not explicitly provided
        if projection is None:
            projection = getattr(self.config, 'projection_type', 'linear')
            
        # Select crop parameters based on image type
        crop_x = self.config.loop_crop_x if is_loop else self.config.static_crop_x
        crop_y = self.config.loop_crop_y if is_loop else self.config.static_crop_y
        crop_width = self.config.loop_crop_width if is_loop else self.config.static_crop_width
        crop_height = self.config.loop_crop_height if is_loop else self.config.static_crop_height
        
        if projection == "azimuthal" and hasattr(self.config, 'center_lat') and self.config.radius_km > 0:
            import math
            # Haversine distance
            R = 6371.0 # Earth radius in km
            lat1 = math.radians(self.config.center_lat)
            lon1 = math.radians(self.config.center_lng)
            lat2 = math.radians(lat)
            lon2 = math.radians(lng)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance_km = R * c
            
            # Bearing
            y = math.sin(dlon) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
            bearing = math.atan2(y, x)
            
            # Pixel mapping (center of crop area is center of radar)
            pixel_radius = crop_width / 2.0
            r_px = (distance_km / self.config.radius_km) * pixel_radius
            
            # Note: bearing is from North (0), rotating clockwise.
            # In image coordinates, y goes down.
            dx = r_px * math.sin(bearing)
            dy = -r_px * math.cos(bearing)
            
            # Center of the crop area
            center_x = crop_width / 2.0
            center_y = crop_height / 2.0
            
            px = int(center_x + dx) + crop_x
            py = int(center_y + dy) + crop_y
            return px, py
        else:
            # Fallback to standard linear interpolation using bounding box (Flat)
            x_pct = (lng - bbox.lng_min) / (bbox.lng_max - bbox.lng_min)
            y_pct = (bbox.lat_max - lat) / (bbox.lat_max - bbox.lat_min)
            
            # Crop offsets
            px = int(x_pct * crop_width) + crop_x
            py = int(y_pct * crop_height) + crop_y
            return px, py

    def get_dbz_at_pixel(self, img: np.ndarray, x: int, y: int) -> float:
        """Reads the color at (x,y) and returns the corresponding dBZ value.
        
        Frames are in RGB format (from PIL). DBZ_COLOR_MAPPING keys are RGB tuples.
        """
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return 0.0
            
        # Frames from PIL are RGB: pixel[0]=R, pixel[1]=G, pixel[2]=B
        pixel = img[y, x]
        if len(pixel) >= 3:
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        else:
            return 0.0
            
        color_tuple = (r, g, b)
        
        # Check ignored colors
        if color_tuple in IGNORED_COLORS:
            return 0.0
            
        # Find nearest color (due to GIF compression artifacts, colors are not exact)
        min_dist = float('inf')
        best_dbz = 0.0
        
        import math
        for known_color, dbz in DBZ_COLOR_MAPPING.items():
            dist = math.sqrt((r - known_color[0])**2 + (g - known_color[1])**2 + (b - known_color[2])**2)
            if dist < min_dist:
                min_dist = dist
                best_dbz = dbz
                
        # Tighter threshold (80) reduces false positives from map features (rivers, terrain)
        if min_dist < 80:
            return best_dbz
            
        return 0.0

    def extract_rain_mask(self, img: np.ndarray) -> np.ndarray:
        """Converts an RGB radar frame into a grayscale mask representing rain intensity."""
        img_float = img.astype(np.float32)
        
        min_dists = np.full(img.shape[:2], 90.0, dtype=np.float32)
        best_intensity = np.zeros(img.shape[:2], dtype=np.uint8)
        
        for color, dbz in DBZ_COLOR_MAPPING.items():
            c_arr = np.array(color, dtype=np.float32)
            dist = np.sqrt(np.sum((img_float - c_arr)**2, axis=-1))
            
            better_mask = dist < min_dists
            min_dists[better_mask] = dist[better_mask]
            
            intensity = int(min(255, max(50, dbz * 4)))
            best_intensity[better_mask] = intensity
            
        # Ignore exact IGNORED_COLORS
        for ignored_color in IGNORED_COLORS:
            ic_arr = np.array(ignored_color, dtype=np.float32)
            exact_match = np.all(img_float == ic_arr, axis=-1)
            best_intensity[exact_match] = 0
            
        # Apply a small median blur to remove single-pixel noise which confuses optical flow
        mask = cv2.medianBlur(best_intensity, 3)
        return mask

    def densify_optical_flow(self, flow: np.ndarray) -> np.ndarray:
        """
        Interpolates optical flow vectors from cloudy regions into empty regions 
        using Normalized Convolution.
        """
        # Calculate magnitude of flow vectors
        mag = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        
        # Create a mask where flow is significant (e.g. moving more than 0.1 pixels)
        mask = (mag > 0.1).astype(np.float32)
        
        if np.sum(mask) < 10:
            return flow  # Too little movement to extrapolate safely
            
        # Global average of valid flow vectors
        global_dx = np.sum(flow[..., 0] * mask) / np.sum(mask)
        global_dy = np.sum(flow[..., 1] * mask) / np.sum(mask)
        
        # 1. Mask the flow
        flow_masked = flow * mask[..., np.newaxis]
        
        # 2. Blur the masked flow and the mask (large kernel to spread wind widely)
        ksize = (101, 101)
        flow_blurred = cv2.blur(flow_masked, ksize)
        mask_blurred = cv2.blur(mask, ksize)
        
        # 3. Divide to get local average (Normalized Convolution)
        mask_blurred_expanded = mask_blurred[..., np.newaxis]
        valid_areas = mask_blurred_expanded > 0.001
        
        dense_flow = np.zeros_like(flow)
        
        # Where blur reached, use local average. Otherwise use global average.
        dense_flow = np.where(
            valid_areas, 
            flow_blurred / (mask_blurred_expanded + 1e-6), 
            np.array([global_dx, global_dy], dtype=np.float32)
        )
        
        # Blend original flow where we had confident data
        dense_flow = np.where(mask[..., np.newaxis] > 0, flow, dense_flow)
        
        return dense_flow

    def calculate_optical_flow(self, frames: List[np.ndarray]) -> np.ndarray:
        """
        Calculates dense optical flow using Farneback algorithm between the last two frames.
        Frames must be isolated for rain to prevent the map background from anchoring the flow.
        """
        if len(frames) < 2:
            raise ValueError("At least 2 frames required for optical flow")
            
        prev_img = frames[-2]
        curr_img = frames[-1]
        
        # Isolate the rain pixels into a grayscale intensity map
        prev_gray = self.extract_rain_mask(prev_img)
        curr_gray = self.extract_rain_mask(curr_img)
            
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
        
        # Extrapolate wind into empty regions so tracking works everywhere
        flow = self.densify_optical_flow(flow)
        
        return flow
        
    def get_flow_vector_at(self, flow: np.ndarray, x: int, y: int) -> Tuple[float, float]:
        """Returns the (dx, dy) velocity vector from optical flow array at given pixel."""
        if x < 0 or x >= flow.shape[1] or y < 0 or y >= flow.shape[0]:
            return 0.0, 0.0
            
        vx = float(flow[y, x, 0])
        vy = float(flow[y, x, 1])
        return vx, vy

    def extrapolate_rain_at_pixel(self, img: np.ndarray, flow: np.ndarray, px: int, py: int, steps: int, rate: float = 0.0, radius: int = 5) -> float:
        """
        Uses Semi-Lagrangian backward tracking to find the dBZ value that will arrive at (px, py) in 'steps' time intervals.
        Each step corresponds to the time difference between the frames used to compute the optical flow (e.g. 15 mins).
        Positive steps mean predicting into the future.
        If 'rate' is provided, it applies an exponential growth/decay factor per step.
        'radius' is used to search a local neighborhood (e.g. +/- 5 pixels) to account for slight movement inaccuracies and cloud edges.
        """
        if steps == 0:
            return self.get_dbz_at_pixel(img, px, py)
            
        # Get the flow vector at the target pixel
        vx, vy = self.get_flow_vector_at(flow, px, py)
        
        # Calculate source pixel (backward tracking)
        # Assuming linear constant velocity over the steps
        src_x = int(round(px - (vx * steps)))
        src_y = int(round(py - (vy * steps)))
        
        max_dbz = 0.0
        # Check a bounding box of +/- radius around the source pixel
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = src_x + dx
                sy = src_y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = self.get_dbz_at_pixel(img, sx, sy)
                    if d > max_dbz:
                        max_dbz = d
                        
        dbz = max_dbz
        
        if rate != 0.0 and dbz > 0:
            factor = 1.0 + rate
            if factor <= 0:
                dbz = 0.0
            else:
                dbz = float(dbz * (factor ** steps))
                
            if dbz > 75.0:
                dbz = 75.0
            elif dbz < 10.0:
                dbz = 0.0
        
        return float(dbz)

    def draw_pin_on_frame(self, img: np.ndarray, x: int, y: int) -> None:
        """Draws a red marker on the image at the specified pixel coordinates."""
        if x < 0 or x >= img.shape[1] or y < 0 or y >= img.shape[0]:
            return
        # Draw thick white shadow/border first for high contrast
        cv2.circle(img, (x, y), radius=6, color=(255, 255, 255), thickness=4)
        cv2.drawMarker(img, (x, y), color=(255, 255, 255), markerType=cv2.MARKER_CROSS, markerSize=14, thickness=4)
        
        # Draw the red pin inside the white border
        color = (0, 0, 255) # BGR Red
        cv2.circle(img, (x, y), radius=6, color=color, thickness=2)
        cv2.drawMarker(img, (x, y), color=color, markerType=cv2.MARKER_CROSS, markerSize=14, thickness=2)

    def get_wind_speed_kmh_from_vector(self, vx: float, vy: float) -> float:
        import math
        pixel_speed_15m = math.sqrt(vx**2 + vy**2)
        
        # Calculate km per pixel (approx 1 degree = 111 km)
        lon_diff = self.config.bbox.lng_max - self.config.bbox.lng_min
        width_km = lon_diff * 111.0
        km_per_pixel = width_km / max(1, self.config.loop_crop_width)
        
        km_per_15m = pixel_speed_15m * km_per_pixel
        km_per_h = km_per_15m * 4.0
        
        return float(km_per_h)

    def get_wind_speed_kmh(self, flow: np.ndarray, px: int, py: int) -> float:
        """
        Converts the optical flow vector (px/15min) into wind speed (km/h) 
        based on the geographic bounding box size.
        """
        vx, vy = self.get_flow_vector_at(flow, px, py)
        return self.get_wind_speed_kmh_from_vector(vx, vy)

    def get_wind_direction_text_from_vector(self, vx: float, vy: float) -> str:
        import math
        if abs(vx) < 0.5 and abs(vy) < 0.5:
            return "ไม่ทราบ"
            
        # Map image vector to standard compass heading (North=0, East=90, South=180, West=270)
        # In image coords: North is vy < 0. East is vx > 0.
        # math.atan2(y, x): using vx as y and -vy as x gives:
        # North (vx=0, vy=-1) -> atan2(0, 1) = 0 deg
        # East (vx=1, vy=0) -> atan2(1, 0) = 90 deg
        # Wind direction for radar should be where it's heading TO (for easier user understanding)
        # instead of the meteorological standard (where it's coming FROM)
        to_angle = math.degrees(math.atan2(vx, -vy)) % 360
        
        # Convert to 16 compass points
        val = int((to_angle / 22.5) + .5)
        arr = ["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        return f"{arr[(val % 16)]} ({int(to_angle)}°)"

    def get_wind_direction_text(self, flow: np.ndarray, px: int, py: int) -> str:
        vx, vy = self.get_flow_vector_at(flow, px, py)
        return self.get_wind_direction_text_from_vector(vx, vy)

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

    def _get_max_dbz_in_radius(self, img: np.ndarray, x: int, y: int, radius: int = 5) -> float:
        max_dbz = 0.0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                sx = x + dx
                sy = y + dy
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    d = self.get_dbz_at_pixel(img, sx, sy)
                    if d > max_dbz:
                        max_dbz = d
        return max_dbz

    def find_approaching_clouds(
        self,
        curr_frame: np.ndarray,
        prev_frame: np.ndarray,
        flow: np.ndarray,
        user_x: int,
        user_y: int,
        search_radius: int = 80,
        min_dbz: float = 20.0,
        cluster_dist: int = 20,
        hit_radius: int = 15,
    ) -> list:
        """
        Scans all rain pixels within search_radius of (user_x, user_y).
        Keeps only pixels whose flow vector points TOWARD the user (dot product > 0).
        Clusters nearby pixels (weighted by dBZ) into distinct cloud groups.
        Returns a list of dicts sorted by ETA (soonest first), each containing:
          cx, cy, dbz_now, dbz_prev, growth_rate, predicted_dbz, dist, eta_min
        """
        import math
        # Restrict search to the valid radar crop area to exclude legend strips
        is_loop = flow.shape[0] <= self.config.loop_crop_height + self.config.loop_crop_y + 10
        crop_x0 = self.config.loop_crop_x if is_loop else self.config.static_crop_x
        crop_y0 = self.config.loop_crop_y if is_loop else self.config.static_crop_y
        crop_w  = self.config.loop_crop_width if is_loop else self.config.static_crop_width
        crop_h  = self.config.loop_crop_height if is_loop else self.config.static_crop_height
        valid_x_min = crop_x0
        valid_x_max = crop_x0 + crop_w
        valid_y_min = crop_y0
        valid_y_max = crop_y0 + crop_h

        candidates = []
        for dy in range(-search_radius, search_radius + 1, 2):
            for dx in range(-search_radius, search_radius + 1, 2):
                sx = user_x + dx
                sy = user_y + dy
                # Skip pixels outside the valid radar area (legend, borders)
                if not (valid_x_min <= sx < valid_x_max and valid_y_min <= sy < valid_y_max):
                    continue
                if not (0 <= sx < curr_frame.shape[1] and 0 <= sy < curr_frame.shape[0]):
                    continue
                d = self.get_dbz_at_pixel(curr_frame, sx, sy)
                if d < min_dbz:
                    continue
                cvx, cvy = self.get_flow_vector_at(flow, sx, sy)
                to_x = user_x - sx
                to_y = user_y - sy
                dist = math.sqrt(to_x ** 2 + to_y ** 2)
                if dist == 0:
                    continue
                dot = (cvx * to_x + cvy * to_y) / dist
                # Only keep pixels whose flow APPROACHES the user (dot > 0)
                if dot <= 0:
                    continue
                
                v_mag = math.sqrt(cvx ** 2 + cvy ** 2)
                if v_mag < 0.1:
                    continue # Not moving enough to predict
                    
                # Perpendicular distance (Cross Track Error)
                perp_dist = abs(to_x * cvy - to_y * cvx) / v_mag
                if perp_dist > hit_radius:
                    continue
                # Previous DBZ at the backward-traced position
                prev_x = int(round(sx - cvx))
                prev_y = int(round(sy - cvy))
                d_prev = self.get_dbz_at_pixel(prev_frame, prev_x, prev_y) if prev_frame is not None else d
                candidates.append((sx, sy, cvx, cvy, d, d_prev, dist, dot))

        if not candidates:
            return []

        clusters = []
        used = [False] * len(candidates)
        for i, c in enumerate(candidates):
            if used[i]:
                continue
            group = [c]
            used[i] = True
            
            # Use BFS to find all connected pixels (Connected Components)
            queue = [c]
            while queue:
                curr = queue.pop(0)
                for j, c2 in enumerate(candidates):
                    if not used[j]:
                        if math.sqrt((curr[0] - c2[0]) ** 2 + (curr[1] - c2[1]) ** 2) < cluster_dist:
                            group.append(c2)
                            used[j] = True
                            queue.append(c2)

            total_w = sum(g[4] for g in group)
            cx = int(sum(g[0] * g[4] for g in group) / total_w)
            cy = int(sum(g[1] * g[4] for g in group) / total_w)
            avg_vx = sum(g[2] for g in group) / len(group)
            avg_vy = sum(g[3] for g in group) / len(group)
            dbz_now  = max(g[4] for g in group)
            dbz_prev = max(g[5] for g in group)
            dist_c   = math.sqrt((cx - user_x) ** 2 + (cy - user_y) ** 2)
            dot_c    = sum(g[7] for g in group) / len(group)
            
            # Avoid division by zero
            if abs(dot_c) < 0.1:
                dot_c = 0.1 if dot_c >= 0 else -0.1
                
            eta_min  = (dist_c / dot_c) * 15.0

            growth_rate   = (dbz_now - dbz_prev) / dbz_prev if dbz_prev > 0 else 0.0
            
            # Predict future intensity only if incoming, otherwise use current
            eta_steps = max(0.0, eta_min / 15.0)
            predicted_dbz = max(0.0, min(75.0, dbz_now * ((1 + growth_rate) ** eta_steps)))

            clusters.append({
                "cx": cx, "cy": cy,
                "vx": avg_vx, "vy": avg_vy,
                "dbz_now": dbz_now,
                "dbz_prev": dbz_prev,
                "growth_rate": growth_rate,
                "predicted_dbz": predicted_dbz,
                "dist": dist_c,
                "eta_min": eta_min,
            })

        clusters.sort(key=lambda c: c["eta_min"])
        return clusters

    @staticmethod
    def render_rain_summary(clouds: list, confidence_cutoff_min: int = 90) -> str:
        """
        Generates a smart, non-redundant rain summary line for Telegram.

        - If no reliable clouds: returns a 'no rain' message.
        - If first cloud = strongest: merges into one line.
        - If a stronger cloud follows: shows two distinct lines.
        """
        def fmt_eta(minutes: float) -> str:
            m = int(round(minutes))
            if m < 60:
                return f"~{m}m"
            h = m // 60
            r = m % 60
            return f"~{h}h{r}m" if r else f"~{h}hr"

        def dbz_label(dbz: float) -> str:
            if dbz >= 55: return "ฝนหนักมาก"
            if dbz >= 40: return "ฝนหนัก"
            if dbz >= 25: return "ฝนปานกลาง"
            return "ฝนเบา"

        # Filter for incoming or currently active rain only (-10 to confidence cutoff)
        reliable = [c for c in clouds if c["predicted_dbz"] >= 15 and -10 <= c["eta_min"] <= confidence_cutoff_min]

        if not reliable:
            return "ℹ️ ไม่พบฝนในระยะ 90 นาทีข้างหน้า"

        first    = reliable[0]
        strongest = max(reliable, key=lambda c: c["predicted_dbz"])

        if first is strongest:
            lbl = dbz_label(first["predicted_dbz"])
            return f"⚡ ฝนกำลังจะมาใน {fmt_eta(first['eta_min'])} ({int(first['predicted_dbz'])} dBZ — {lbl})"
        else:
            lbl_f = dbz_label(first["predicted_dbz"])
            lbl_s = dbz_label(strongest["predicted_dbz"])
            return (
                f"⏱ ฝนก้อนแรกใน {fmt_eta(first['eta_min'])} ({int(first['predicted_dbz'])} dBZ — {lbl_f})\n"
                f"⚡ ก้อนหนักกว่ามาทีหลัง {fmt_eta(strongest['eta_min'])} ({int(strongest['predicted_dbz'])} dBZ — {lbl_s})"
            )

    @staticmethod
    def generate_radar_tracking_image(frame: np.ndarray, user_x: int, user_y: int, clouds: list) -> Optional[bytes]:
        if frame is None or not clouds:
            return None
        import cv2
        
        # Crop a 240x240 region around the user
        crop_r = 120
        h, w = frame.shape[:2]
        
        x1 = max(0, user_x - crop_r)
        y1 = max(0, user_y - crop_r)
        x2 = min(w, user_x + crop_r)
        y2 = min(h, user_y + crop_r)
        
        crop_img = frame[y1:y2, x1:x2].copy()
        
        # Scale up by 3x for sharp, zoomed-in image in Telegram
        scale = 3.0
        img = cv2.resize(crop_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        
        ux = int((user_x - x1) * scale)
        uy = int((user_y - y1) * scale)
        
        # Draw user pin (but remove the large search radius circle to reduce clutter)
        cv2.drawMarker(img, (ux, uy), (0, 0, 255), cv2.MARKER_CROSS, int(20 * scale), int(2 * scale))
        
        # Filter for incoming clouds only (ETA >= -5) and limit to top 3 strongest to avoid overlap
        incoming = [c for c in clouds if c["eta_min"] >= -5]
        incoming.sort(key=lambda c: c["predicted_dbz"], reverse=True)
        top_clouds = incoming[:3]
        
        for c in top_clouds:
            cx_orig, cy_orig = c["cx"], c["cy"]
            
            # Only draw if the cloud is within or near the crop
            if cx_orig < x1 - 50 or cx_orig > x2 + 50 or cy_orig < y1 - 50 or cy_orig > y2 + 50:
                continue
                
            cx = int((cx_orig - x1) * scale)
            cy = int((cy_orig - y1) * scale)
            eta = c["eta_min"]
            dbz = c["predicted_dbz"]
            
            if dbz >= 60: color = (155, 89, 182) # Purple
            elif dbz >= 50: color = (231, 76, 60) # Red
            elif dbz >= 40: color = (243, 156, 18) # Orange
            elif dbz >= 30: color = (241, 196, 15) # Yellow
            else: color = (46, 204, 113) # Green
            
            cv2.circle(img, (cx, cy), int(12 * scale), color, int(1.5 * scale))
            
            # Draw wind direction arrow (vx, vy are pixels per 15 mins)
            vx_scaled = int(c.get("vx", 0) * scale * 3.0)  # Show ~45 min trajectory
            vy_scaled = int(c.get("vy", 0) * scale * 3.0)
            
            # If there's no movement, just point to user as fallback
            if vx_scaled == 0 and vy_scaled == 0:
                cv2.arrowedLine(img, (cx, cy), (ux, uy), (255, 255, 0), int(1.5 * scale), tipLength=0.1)  # RGB Yellow
            else:
                target_x = cx + vx_scaled
                target_y = cy + vy_scaled
                cv2.arrowedLine(img, (cx, cy), (target_x, target_y), (255, 255, 0), int(1.5 * scale), tipLength=0.3)  # RGB Yellow
            
            sign = "-" if eta < 0 else "~"
            abs_eta = int(abs(eta))
            if abs_eta < 60:
                time_str = f"{abs_eta} m"
            else:
                time_str = f"{abs_eta // 60} hr {abs_eta % 60} m"
                
            cv2.putText(img, f"{sign}{time_str}", (cx + int(15 * scale), cy), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale, (255, 255, 255), int(1.5 * scale))

        # Convert RGB back to BGR for cv2.imencode
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        is_success, buffer = cv2.imencode(".png", img_bgr)
        return buffer.tobytes() if is_success else None

    @staticmethod
    def generate_timeline_image(clouds: list) -> Optional[bytes]:
        if not clouds:
            return None
        import io
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return None
            
        width, height = 800, 430
        img = Image.new("RGBA", (width, height), (30, 30, 30, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        
        try:
            # Fallback for systems that don't have Helvetica
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 16)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 14)
            except:
                font = ImageFont.load_default()
                font_small = font
            
        baseline_y = 350
        draw.line([(0, baseline_y), (width, baseline_y)], fill=(100, 100, 100, 255), width=2)
        
        def time_to_x(t):
            return int(50 + (t - (-60)) * (700 / 210.0))
            
        x_90 = time_to_x(90)
        draw.line([(x_90, 50), (x_90, height - 20)], fill=(74, 144, 226, 128), width=2)
        draw.text((x_90 + 5, 60), "Confidence\nBoundary", fill=(74, 144, 226, 200), font=font_small)
        
        base_x = time_to_x(0)
        draw.line([(base_x, 40), (base_x, height - 20)], fill=(255, 255, 255, 200), width=2)
        draw.text((base_x - 15, 25), "NOW", font=font, fill=(255, 255, 255, 255))

        # Bin clouds by X coordinate to prevent overlapping exact same ETA
        binned_clouds = {}
        for c in clouds:
            eta = c["eta_min"]
            dbz = c["predicted_dbz"]
            x = time_to_x(eta)
            x = max(20, min(780, x))
            if x not in binned_clouds or dbz > binned_clouds[x]["dbz"]:
                binned_clouds[x] = {"eta": eta, "dbz": dbz}

        last_x = -999
        y_offsets = {}
        
        for x in sorted(binned_clouds.keys()):
            eta = binned_clouds[x]["eta"]
            dbz = binned_clouds[x]["dbz"]
            
            h = int(dbz * 4)
            
            if dbz >= 60: color = (155, 89, 182, 230) # Purple
            elif dbz >= 50: color = (231, 76, 60, 230) # Red
            elif dbz >= 40: color = (243, 156, 18, 230) # Orange
            elif dbz >= 30: color = (241, 196, 15, 230) # Yellow
            else: color = (46, 204, 113, 230) # Green
            
            if eta > 90:
                color = (color[0], color[1], color[2], 100)
                
            draw.rectangle([(x-10, baseline_y-h), (x+10, baseline_y)], fill=color)
            draw.text((x-12, baseline_y-h-20), f"{int(dbz)}", fill=(255, 255, 255, 255), font=font)
            
            # Smart text offset to avoid overlapping labels
            y_off = 20
            if x - last_x < 40:
                # Cycle through 20, 35, 50 to prevent cascading off screen
                prev_off = y_offsets.get(last_x, 50)
                y_off = 35 if prev_off == 20 else (50 if prev_off == 35 else 20)
            y_offsets[x] = y_off
            last_x = x
            
            m = int(round(abs(eta)))
            t_str = f"~{m}m" if m < 60 else f"~{m//60}h{m%60}m"
            sign = "-" if eta < 0 else ""
            draw.text((x-15, baseline_y+y_off), f"{sign}{t_str}", fill=(200, 200, 200, 255), font=font_small)
            
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def calculate_lagrangian_growth(self, frames: list, flow: np.ndarray, target_x: int, target_y: int, steps_ahead: int, max_lookback_frames: int = 2) -> float:
        """
        Calculates the true growth of the specific air mass that will hit target_x, target_y in `steps_ahead` frames.
        It tracks the air mass backwards in time to compare its current intensity with its past intensity.
        `max_lookback_frames` determines how far back to trace (e.g. 2 = 30 mins).
        """
        if len(frames) < 2:
            return 0.0
            
        vx, vy = self.get_flow_vector_at(flow, target_x, target_y)
        
        # Where is the cloud that will hit the target located CURRENTLY?
        curr_src_x = int(round(target_x - vx * steps_ahead))
        curr_src_y = int(round(target_y - vy * steps_ahead))
        
        # Search in a 30-pixel radius (~30km) to lock onto the MACRO storm cell
        # rather than tracking a micro air parcel which may disperse or shift.
        curr_dbz = self._get_max_dbz_in_radius(frames[-1], curr_src_x, curr_src_y, radius=30)
        
        past_dbz = 0.0
        
        # Look backwards through frames to find the oldest valid dBZ
        max_lookback = min(max_lookback_frames, len(frames) - 1)
        for i in range(1, max_lookback + 1):
            prev_x = int(round(curr_src_x - i * vx))
            prev_y = int(round(curr_src_y - i * vy))
            # Index offset: i=1 -> frames[-2]
            dbz = self._get_max_dbz_in_radius(frames[-(i + 1)], prev_x, prev_y, radius=30)
            if dbz > 0:
                past_dbz = dbz # Keep overwriting to get the OLDEST available > 0
                
        if curr_dbz == 0 and past_dbz == 0:
            return 0.0
        elif curr_dbz > 0 and past_dbz == 0:
            return 50.0  # Formed
        elif curr_dbz == 0 and past_dbz > 0:
            return -100.0 # Dissipated
            
        growth_pct = ((curr_dbz - past_dbz) / past_dbz) * 100.0
        return max(-100.0, min(100.0, growth_pct))

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

    async def fetch_loop_gif_and_extract_frames(self) -> Tuple[List[np.ndarray], Optional['datetime']]:
        """Fetches the Loop.gif and extracts frames and the Last-Modified datetime."""
        import httpx
        from PIL import Image, ImageSequence
        import io
        from datetime import datetime, timezone
        
        url = getattr(self.config, 'loop_gif_url', self.config.static_image_url.replace('_latest.gif', 'Loop.gif').replace('_latest.jpg', 'Loop.gif'))
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    last_modified = response.headers.get("last-modified")
                    dt = None
                    
                    # Try to fetch exact time from the HTML og:image first (more accurate than Last-Modified)
                    try:
                        php_url = f"https://weather.tmd.go.th/{self.station_code[:3]}.php"
                        php_resp = await client.get(php_url)
                        if php_resp.status_code == 200:
                            import re
                            from zoneinfo import ZoneInfo
                            match = re.search(r'v=(\d{6})_(\d{4})', php_resp.text)
                            if match:
                                date_str = match.group(1)
                                time_str = match.group(2)
                                year = int('20' + date_str[0:2])
                                month = int(date_str[2:4])
                                day = int(date_str[4:6])
                                hour = int(time_str[0:2])
                                minute = int(time_str[2:4])
                                bkk_tz = ZoneInfo('Asia/Bangkok')
                                dt_bkk = datetime(year, month, day, hour, minute, tzinfo=bkk_tz)
                                dt = dt_bkk.astimezone(timezone.utc)
                    except Exception as e:
                        print(f"Error fetching exact timestamp from HTML: {e}")
                        
                    if dt is None and last_modified:
                        try:
                            # format: Sat, 06 Jun 2026 09:35:43 GMT
                            dt = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                        except Exception as e:
                            print(f"Error parsing date: {e}")
                            
                    img = Image.open(io.BytesIO(response.content))
                    frames = []
                    # PIL handles GIF frame disposal properly (coalescing delta frames)
                    for frame in ImageSequence.Iterator(img):
                        frames.append(np.array(frame.copy().convert("RGB")))
                        
                    try:
                        from app.services.ocr_service import OCRService
                        ocr_svc = OCRService()
                        if len(frames) > 0:
                            import time
                            fallback_ts = int(dt.timestamp()) if dt else int(time.time())
                            ts = await ocr_svc.get_frame_timestamp(frames[-1], fallback_ts=fallback_ts)
                            if ts is not None:
                                dt = datetime.fromtimestamp(ts, timezone.utc)
                    except Exception as e:
                        print(f"Error in OCR: {e}")

                    return frames, dt
        except Exception as e:
            print(f"Error fetching loop gif: {e}")
        return [], None

    async def fetch_loop_history_bytes(self) -> List[bytes]:
        """
        Fetches the history of images from the loop page.
        This is a stub. Real implementation requires scraping the loop.php HTML.
        For MVP, we just try to fetch the latest static image as history.
        """
        # TODO: Implement actual HTML scraping of self.config.loop_page_url
        # For now, return an empty list to fallback to polling
        return []

    async def save_polled_frame(self, image_bytes: bytes) -> str:
        """Saves a polled image byte sequence to Google Cloud Storage with a timestamp."""
        import time
        import os
        from google.cloud import storage
        
        timestamp = int(time.time())
        filename = f"radar/{self.station_code}/{self.station_code}_{timestamp}.gif"
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
        
        # Use sync GCS upload (in a real high-throughput app we might use asyncio wrapper or threadpool)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        blob.upload_from_string(image_bytes, content_type="image/gif")
        
        return filename
        
    async def cleanup_old_frames(self, max_age_hours: int = 3) -> int:
        """Deletes files in GCS that are older than max_age_hours."""
        import time
        import os
        from google.cloud import storage
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cutoff_time = now - max_age_seconds
        
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "fonmayang.appspot.com")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        prefix = f"radar/{self.station_code}/"
        
        blobs = bucket.list_blobs(prefix=prefix)
        deleted_count = 0
        
        for blob in blobs:
            # We parse the timestamp from the filename "radar/kkn120/kkn120_1234567890.gif"
            try:
                base_name = blob.name.split("/")[-1]
                ts_str = base_name.replace(f"{self.station_code}_", "").replace(".gif", "")
                blob_ts = int(ts_str)
                if blob_ts < cutoff_time:
                    blob.delete()
                    deleted_count += 1
            except Exception:
                pass
                
        return deleted_count

