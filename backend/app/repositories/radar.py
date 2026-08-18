# backend/app/repositories/radar.py

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import RadarStationModel

class RadarStationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_station(self, code: str) -> Optional[RadarStationModel]:
        stmt = select(RadarStationModel).where(RadarStationModel.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_stations(self) -> List[RadarStationModel]:
        stmt = select(RadarStationModel).order_by(RadarStationModel.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_stations(self) -> List[RadarStationModel]:
        stmt = select(RadarStationModel).where(RadarStationModel.is_active == 1).order_by(RadarStationModel.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_station(self, data: Dict[str, Any]) -> RadarStationModel:
        code = data["code"]
        existing = await self.get_station(code)

        now = datetime.now(timezone.utc)  # timezone-aware UTC (replaces deprecated utcnow())
        if not existing:
            station = RadarStationModel(
                code=code,
                name=data.get("name", code),
                static_image_url=data.get("static_image_url", ""),
                loop_page_url=data.get("loop_page_url", ""),
                loop_gif_url=data.get("loop_gif_url", ""),
                center_lat=data.get("center_lat", 0.0),
                center_lng=data.get("center_lng", 0.0),
                radius_km=data.get("radius_km", 240.0),
                lat_max=data.get("lat_max", 0.0),
                lng_min=data.get("lng_min", 0.0),
                lat_min=data.get("lat_min", 0.0),
                lng_max=data.get("lng_max", 0.0),
                static_crop_x=data.get("static_crop_x", 0),
                static_crop_y=data.get("static_crop_y", 0),
                static_crop_width=data.get("static_crop_width", 800),
                static_crop_height=data.get("static_crop_height", 800),
                loop_crop_x=data.get("loop_crop_x", 0),
                loop_crop_y=data.get("loop_crop_y", 0),
                loop_crop_width=data.get("loop_crop_width", 680),
                loop_crop_height=data.get("loop_crop_height", 680),
                projection_type=data.get("projection_type", "azimuthal"),
                is_active=1 if data.get("is_active", True) else 0,
                created_at=now,
                updated_at=now
            )
            self.session.add(station)
        else:
            station = existing
            for field in [
                "name", "static_image_url", "loop_page_url", "loop_gif_url",
                "center_lat", "center_lng", "radius_km", "lat_max", "lng_min", "lat_min", "lng_max",
                "static_crop_x", "static_crop_y", "static_crop_width", "static_crop_height",
                "loop_crop_x", "loop_crop_y", "loop_crop_width", "loop_crop_height", "projection_type"
            ]:
                if field in data:
                    setattr(station, field, data[field])
            
            if "is_active" in data:
                station.is_active = 1 if data["is_active"] else 0
            station.updated_at = now

        await self.session.commit()
        await self.session.refresh(station)
        return station

    async def toggle_active(self, code: str, is_active: bool) -> Optional[RadarStationModel]:
        station = await self.get_station(code)
        if station:
            station.is_active = 1 if is_active else 0
            station.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(station)
        return station
