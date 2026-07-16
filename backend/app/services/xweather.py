import os
import logging
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class XweatherService(BaseWeatherService):
    MINUTECAST_API_URL = "https://data.api.xweather.com/conditions"
    ADVISORIES_API_URL = "https://data.api.xweather.com/alerts"
    LIGHTNING_API_URL = "https://data.api.xweather.com/lightning/closest"
    STORMCELLS_API_URL = "https://data.api.xweather.com/stormcells/closest"
    
    def __init__(self):
        self.client_id = os.getenv("XWEATHER_CLIENT_ID")
        self.client_secret = os.getenv("XWEATHER_CLIENT_SECRET")
        self.enabled = os.getenv("XWEATHER_ENABLED", "false").lower() == "true"
        self.timeout = httpx.Timeout(15.0)
        
        # Circuit Breaker state
        self.circuit_breaker_until: Optional[datetime] = None

    def _is_circuit_open(self) -> bool:
        """Check if the circuit breaker is currently open."""
        if self.circuit_breaker_until and datetime.now(timezone.utc) < self.circuit_breaker_until:
            return True
        return False
        
    def _open_circuit(self, minutes: int = 60):
        """Open the circuit breaker for a specified duration."""
        self.circuit_breaker_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        logger.warning(f"Xweather API circuit opened (disabled) for {minutes} minutes.")

    async def get_current_radar_metadata(self) -> dict:
        return {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "map_layer": None
        }

    async def predict_rain_by_location(self, lat: float, lng: float, mock_state: Optional[str] = None) -> dict:
        """Fetch minutecast from Xweather."""
        if not self.enabled:
            logger.debug("XweatherService is disabled via config.")
            raise ValueError("Xweather is disabled")
            
        if not self.client_id or not self.client_secret:
            logger.error("XWEATHER_CLIENT_ID or XWEATHER_CLIENT_SECRET is missing")
            raise ValueError("Xweather credentials missing")
            
        if self._is_circuit_open():
            raise Exception("Xweather circuit is open due to previous quota limits or errors.")
            
        if mock_state == "rain":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 15.0}],
                "intensity": "หนัก (Heavy)",
                "max_rain": 15.0,
                "duration_minutes": 60,
                "wind_speed_kmh": 20.0,
                "endpoint": "xweather"
            }
        elif mock_state == "clear":
            return {
                "predictions": [{"time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "rain": 0.0}],
                "intensity": "ไม่มีฝน (No Rain)",
                "max_rain": 0.0,
                "duration_minutes": 0,
                "wind_speed_kmh": 5.0,
                "endpoint": "xweather"
            }
        elif mock_state == "error":
            raise Exception("Mock Network Error: Unable to reach Xweather API")

        params = {
            "p": f"{lat},{lng}",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "filter": "minutelyprecip"
        }

        client = get_http_client()
        try:
            response = await client.get(self.MINUTECAST_API_URL, params=params, timeout=self.timeout)
            
            if response.status_code in [401, 403, 429]:
                logger.error(f"Xweather rate limit/auth hit: {response.status_code} - {response.text}")
                self._open_circuit(minutes=60)
                response.raise_for_status()
                
            response.raise_for_status()
            data = response.json()
            
            predictions = []
            max_rain = 0.0
            rain_start = None
            rain_end = None
            wind_speed_sum = 0.0
            wind_speed_count = 0
            wind_dir_sum = 0.0
            wind_dir_count = 0
            
            res_data = data.get("response", [])
            periods = []
            if isinstance(res_data, list) and res_data:
                periods = res_data[0].get("periods", [])
            elif isinstance(res_data, dict):
                periods = res_data.get("periods", [])
                
            for period in periods:
                time_str = period.get("dateTimeISO", "")
                precip = period.get("precipMM", 0.0)
                
                # Wind
                wind_speed = period.get("windSpeedKPH", 0.0)
                wind_dir = period.get("windDirDEG", 0.0)
                
                predictions.append({
                    "time": time_str,
                    "rain": precip
                })
                
                if precip > 0:
                    max_rain = max(max_rain, precip)
                    try:
                        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00")).timestamp()
                        if not rain_start:
                            rain_start = dt
                        rain_end = dt
                    except Exception:
                        pass
                        
                    if wind_speed:
                        wind_speed_sum += wind_speed
                        wind_speed_count += 1
                    if wind_dir is not None:
                        wind_dir_sum += wind_dir
                        wind_dir_count += 1

            intensity_text = "ไม่มีฝน (No Rain)"
            duration_minutes = 0
            avg_wind_speed = 0.0
            wind_dir_text = "ไม่ทราบ"
            
            if max_rain > 0:
                if max_rain < 2.5:
                    intensity_text = "เบา (Light)"
                elif max_rain <= 10.0:
                    intensity_text = "ปานกลาง (Moderate)"
                else:
                    intensity_text = "หนัก (Heavy)"
                    
                if rain_start and rain_end:
                    duration_minutes = int((rain_end - rain_start) / 60)
                    
                if wind_speed_count > 0:
                    avg_wind_speed = wind_speed_sum / wind_speed_count
                    
            wind_speed_kmh = avg_wind_speed
            
            if wind_dir_count > 0:
                avg_wind_dir = wind_dir_sum / wind_dir_count
                wind_dir_text = self.degrees_to_cardinal(avg_wind_dir)

            return {
                "predictions": predictions,
                "intensity": intensity_text,
                "max_rain": max_rain,
                "duration_minutes": duration_minutes,
                "wind_speed_kmh": round(wind_speed_kmh, 1),
                "wind_dir_text": wind_dir_text,
                "endpoint": "xweather"
            }

        except httpx.HTTPStatusError as e:
            import re
            err_str = str(e)
            err_str = re.sub(r'client_id=[^&\s]+', 'client_id=***', err_str)
            err_str = re.sub(r'client_secret=[^&\s]+', 'client_secret=***', err_str)
            logger.error(f"Xweather HTTP error {e.response.status_code}: {err_str}")
            raise Exception(err_str)
        except Exception as e:
            import re
            err_str = str(e)
            err_str = re.sub(r'client_id=[^&\s]+', 'client_id=***', err_str)
            err_str = re.sub(r'client_secret=[^&\s]+', 'client_secret=***', err_str)
            logger.error(f"Xweather Request failed: {err_str}")
            raise Exception(err_str)

    async def get_advanced_alerts(self, lat: float, lng: float, mock_state: Optional[str] = None) -> Dict[str, Any]:
        """Fetch advanced alerts: advisories, lightning, stormcells."""
        if not self.enabled or self._is_circuit_open():
            return {"advisories": [], "lightning": None, "stormcell": None}
            
        if mock_state == "rain":
            return {
                "advisories": [{"type": "TSTORM", "name": "Severe Thunderstorm Warning (Mock)", "body": "This is a mock warning."}],
                "lightning": {"distance_km": 2.5},
                "stormcell": {"distance_km": 10.0, "direction": "NE", "speed_kmh": 40.0, "max_dbz": 60}
            }
        elif mock_state == "clear":
            return {"advisories": [], "lightning": None, "stormcell": None}
        elif mock_state == "error":
            raise Exception("Mock Network Error: Unable to reach Xweather Advanced API")
            
        params = {
            "p": f"{lat},{lng}",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "limit": 1
        }
        
        result = {"advisories": [], "lightning": None, "stormcell": None}
        
        from app.dependencies import get_http_client
        client = get_http_client()
        # 1. Advisories
        try:
            # Need to use radius for advisories, e.g., 5km
            adv_params = {**params, "radius": "5km"}
            response = await client.get(self.ADVISORIES_API_URL, params=adv_params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                res_list = data.get("response", [])
                if isinstance(res_list, list) and res_list:
                    for adv in res_list:
                        details = adv.get("details", {})
                        result["advisories"].append({
                            "type": details.get("type", "Unknown"),
                            "name": details.get("name", "Advisory"),
                            "body": details.get("body", "")
                        })
            elif response.status_code in [401, 403, 429]:
                self._open_circuit(60)
                return result # Return empty immediately
        except Exception as e:
            logger.warning(f"Failed to fetch advisories: {e}")

        # 2. Lightning (Closest within 10km)
        if not self._is_circuit_open():
            try:
                light_params = {**params, "radius": "10km"}
                response = await client.get(self.LIGHTNING_API_URL, params=light_params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    res_list = data.get("response", [])
                    if isinstance(res_list, list) and res_list:
                        closest = res_list[0]
                        dist_km = closest.get("relativeTo", {}).get("distanceKM")
                        if dist_km is not None:
                            result["lightning"] = {"distance_km": dist_km}
                elif response.status_code in [401, 403, 429]:
                    self._open_circuit(60)
                    return result
            except Exception as e:
                logger.warning(f"Failed to fetch lightning: {e}")

        # 3. Stormcells (Closest within 15km)
        if not self._is_circuit_open():
            try:
                storm_params = {**params, "radius": "15km"}
                response = await client.get(self.STORMCELLS_API_URL, params=storm_params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    res_list = data.get("response", [])
                    if isinstance(res_list, list) and res_list:
                        cell = res_list[0]
                        traits = cell.get("traits", {})
                        movement = cell.get("movement", {})
                        dist_km = cell.get("relativeTo", {}).get("distanceKM")
                        result["stormcell"] = {
                            "distance_km": dist_km,
                            "direction": movement.get("directionTo", ""),
                            "speed_kmh": movement.get("speedKPH", 0),
                            "max_dbz": traits.get("dbz", 0)
                        }
                elif response.status_code in [401, 403, 429]:
                    self._open_circuit(60)
                    return result
            except Exception as e:
                logger.warning(f"Failed to fetch stormcells: {e}")

        return result

    async def get_active_tropical_cyclones(self) -> list[dict]:
        """Fetch active tropical cyclones in the region (SEA)."""
        if not self.enabled or self._is_circuit_open():
            return []
            
        params = {
            "p": "15.0,100.0", # Center of SEA
            "radius": "2000km",
            "filter": "active",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "limit": 10
        }
        
        events = []
        from app.dependencies import get_http_client
        client = get_http_client()
        try:
            response = await client.get("https://data.api.xweather.com/tropicalcyclones", params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                res_list = data.get("response", [])
                if isinstance(res_list, list):
                    for c in res_list:
                        profile = c.get("profile", {})
                        position = c.get("position", {})
                        location = position.get("location", [0, 0])
                        
                        events.append({
                            "id": c.get("id"),
                            "name": profile.get("name", "Unknown Cyclone"),
                            "category": profile.get("category", "TD"),
                            "max_wind_kmh": position.get("windSpeedKPH", 0),
                            "lat": location[1] if len(location) >= 2 else 0,
                            "lng": location[0] if len(location) >= 2 else 0,
                            "source": "Xweather"
                        })
            elif response.status_code in [401, 403, 429]:
                self._open_circuit(60)
        except Exception as e:
                logger.warning(f"Failed to fetch tropical cyclones: {e}")
        return events

    async def get_active_fires(self) -> list[dict]:
        """Fetch active fires/hotspots in the region."""
        if not self.enabled or self._is_circuit_open():
            return []
            
        params = {
            "p": "15.0,100.0",
            "radius": "1000km",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "limit": 50
        }
        
        events = []
        from app.dependencies import get_http_client
        client = get_http_client()
        try:
            response = await client.get("https://data.api.xweather.com/fires", params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                res_list = data.get("response", [])
                if isinstance(res_list, list):
                    for f in res_list:
                        loc = f.get("loc", {})
                        profile = f.get("profile", {})
                        
                        events.append({
                            "id": f.get("id"),
                            "name": profile.get("name") or profile.get("type", "Wildfire"),
                            "confidence": profile.get("confidence", 0),
                            "lat": loc.get("lat", 0),
                            "lng": loc.get("long", 0), # Xweather usually uses 'long'
                            "source": "Xweather"
                        })
            elif response.status_code in [401, 403, 429]:
                self._open_circuit(60)
        except Exception as e:
                logger.warning(f"Failed to fetch active fires: {e}")
        return events
