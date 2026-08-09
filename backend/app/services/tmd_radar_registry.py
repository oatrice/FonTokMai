# backend/app/services/tmd_radar_registry.py

import logging
from typing import Dict, Optional
from app.services.tmd_radar_config import STATIONS as HARDCODED_STATIONS, StationConfig, BoundingBox

logger = logging.getLogger(__name__)

class DynamicRadarRegistry:
    def __init__(self):
        self._cached_stations: Dict[str, StationConfig] = {}
        self._loaded_from_db = False

    async def get_all_stations(self, session=None) -> Dict[str, StationConfig]:
        """
        Returns all active stations. Loads from DB (Neon Postgres) if available, 
        with automatic fallback to hardcoded STATIONS defaults.
        """
        if self._loaded_from_db and self._cached_stations:
            return self._cached_stations

        if session:
            try:
                from app.repositories.radar import RadarStationRepository
                repo = RadarStationRepository(session)
                db_stations = await repo.get_active_stations()
                
                if db_stations:
                    dynamic_map = {}
                    for model in db_stations:
                        bbox = BoundingBox(
                            lat_max=model.lat_max,
                            lng_min=model.lng_min,
                            lat_min=model.lat_min,
                            lng_max=model.lng_max
                        )
                        dynamic_map[model.code] = StationConfig(
                            code=model.code,
                            name=model.name,
                            static_image_url=model.static_image_url,
                            loop_page_url=model.loop_page_url or "",
                            loop_gif_url=model.loop_gif_url or "",
                            bbox=bbox,
                            projection_type=model.projection_type or "azimuthal",
                            center_lat=model.center_lat,
                            center_lng=model.center_lng,
                            radius_km=model.radius_km,
                            static_crop_x=model.static_crop_x,
                            static_crop_y=model.static_crop_y,
                            static_crop_width=model.static_crop_width,
                            static_crop_height=model.static_crop_height,
                            loop_crop_x=model.loop_crop_x,
                            loop_crop_y=model.loop_crop_y,
                            loop_crop_width=model.loop_crop_width,
                            loop_crop_height=model.loop_crop_height
                        )
                    self._cached_stations = dynamic_map
                    self._loaded_from_db = True
                    logger.info(f"Loaded {len(dynamic_map)} radar stations dynamically from Neon DB.")
                    return self._cached_stations
            except Exception as e:
                logger.warning(f"Failed to load radar stations from DB: {e}. Falling back to hardcoded STATIONS.")

        # Fallback to hardcoded defaults
        return HARDCODED_STATIONS

    def invalidate_cache(self):
        self._cached_stations.clear()
        self._loaded_from_db = False

# Global Singleton Registry
radar_registry = DynamicRadarRegistry()
