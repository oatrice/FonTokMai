import os
import logging
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from .weather_base import BaseWeatherService

logger = logging.getLogger(__name__)

class XweatherService(BaseWeatherService):
    MINUTECAST_API_URL = "https://data.api.xweather.com/minutecast"
    ADVISORIES_API_URL = "https://data.api.xweather.com/advisories"
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

        params = {
            "p": f"{lat},{lng}",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.MINUTECAST_API_URL, params=params)
                
                if response.status_code in [429, 403]:
                    logger.error(f"Xweather rate limit hit: {response.status_code} - {response.text}")
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
                
                periods = data.get("response", {}).get("periods", [])
                for period in periods:
                    time_str = period.get("dateTimeISO", "")
                    precip = period.get("precipMM", 0.0)
                    wind = period.get("windSpeedKPH", 0.0)
                    
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
                        except ValueError:
                            pass
                        
                        wind_speed_sum += wind
                        wind_speed_count += 1
                        
                intensity_text = "ไม่มีฝน (No Rain)"
                duration_minutes = 0
                avg_wind_speed = 0.0
                
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
                        
                return {
                    "predictions": predictions,
                    "intensity": intensity_text,
                    "max_rain": max_rain,
                    "duration_minutes": duration_minutes,
                    "wind_speed_kmh": round(avg_wind_speed, 1),
                    "endpoint": "xweather"
                }

            except httpx.HTTPStatusError as e:
                logger.error(f"Xweather HTTP error {e.response.status_code}: {e.response.text}")
                raise e
            except Exception as e:
                logger.error(f"Xweather Request failed: {e}")
                raise e

    async def get_advanced_alerts(self, lat: float, lng: float, mock_state: Optional[str] = None) -> Dict[str, Any]:
        """Fetch advanced alerts: advisories, lightning, stormcells."""
        if not self.enabled or self._is_circuit_open():
            return {"advisories": [], "lightning": None, "stormcell": None}
            
        params = {
            "p": f"{lat},{lng}",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "limit": 1
        }
        
        result = {"advisories": [], "lightning": None, "stormcell": None}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. Advisories
            try:
                # Need to use radius for advisories, e.g., 5km
                adv_params = {**params, "radius": "5km"}
                response = await client.get(self.ADVISORIES_API_URL, params=adv_params)
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
                elif response.status_code in [429, 403]:
                    self._open_circuit(60)
                    return result # Return empty immediately
            except Exception as e:
                logger.warning(f"Failed to fetch advisories: {e}")

            # 2. Lightning (Closest within 10km)
            if not self._is_circuit_open():
                try:
                    light_params = {**params, "radius": "10km"}
                    response = await client.get(self.LIGHTNING_API_URL, params=light_params)
                    if response.status_code == 200:
                        data = response.json()
                        res_list = data.get("response", [])
                        if isinstance(res_list, list) and res_list:
                            closest = res_list[0]
                            dist_km = closest.get("relativeTo", {}).get("distanceKM")
                            if dist_km is not None:
                                result["lightning"] = {"distance_km": dist_km}
                    elif response.status_code in [429, 403]:
                        self._open_circuit(60)
                        return result
                except Exception as e:
                    logger.warning(f"Failed to fetch lightning: {e}")

            # 3. Stormcells (Closest within 15km)
            if not self._is_circuit_open():
                try:
                    storm_params = {**params, "radius": "15km"}
                    response = await client.get(self.STORMCELLS_API_URL, params=storm_params)
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
                    elif response.status_code in [429, 403]:
                        self._open_circuit(60)
                        return result
                except Exception as e:
                    logger.warning(f"Failed to fetch stormcells: {e}")

        return result
