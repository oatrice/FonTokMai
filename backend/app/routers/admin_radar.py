# backend/app/routers/admin_radar.py

import cv2
import numpy as np
import httpx
import logging
import requests
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.database import AsyncSessionLocal
from app.repositories.radar import RadarStationRepository
from app.services.tmd_radar.auto_calibration import AutoCalibrationService
from app.services.tmd_radar_registry import radar_registry
from app.services.weather_manager import invalidate_station_memory_cache

router = APIRouter(tags=["Admin Radar"])

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

class RadarPreviewRequest(BaseModel):
    code: str = Field(..., json_schema_extra={"example": "svp240"})
    name: str = Field(..., json_schema_extra={"example": "Bangkok Suvarnabhumi (240km)"})
    image_url: str = Field(..., json_schema_extra={"example": "https://weather.tmd.go.th/svp/svp240_latest.jpg"})
    loop_page_url: Optional[str] = Field(default="")
    loop_gif_url: Optional[str] = Field(default="")
    lat: float = Field(..., json_schema_extra={"example": 13.6860})
    lng: float = Field(..., json_schema_extra={"example": 100.7486})
    radius_km: float = Field(default=240.0)
    # Optional manual override crop coordinates for fine-tuning
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_width: Optional[int] = None
    crop_height: Optional[int] = None
    loop_crop_x: Optional[int] = None
    loop_crop_y: Optional[int] = None
    loop_crop_width: Optional[int] = None
    loop_crop_height: Optional[int] = None

class RadarStationSaveRequest(BaseModel):
    code: str
    name: str
    static_image_url: str
    loop_page_url: Optional[str] = ""
    loop_gif_url: Optional[str] = ""
    center_lat: float
    center_lng: float
    radius_km: float = 240.0
    lat_max: float
    lng_min: float
    lat_min: float
    lng_max: float
    static_crop_x: int = 0
    static_crop_y: int = 0
    static_crop_width: int = 800
    static_crop_height: int = 800
    loop_crop_x: int = 0
    loop_crop_y: int = 0
    loop_crop_width: int = 680
    loop_crop_height: int = 680
    projection_type: str = "azimuthal"
    is_active: bool = True

class RadarPreviewResponse(BaseModel):
    code: str
    name: str
    circle_detected: bool
    detected_circle: Optional[Any] = None
    crop_info: Dict[str, Any]
    calculated_bbox: Dict[str, float]
    preview_image_base64: str
    loop_preview_image_base64: Optional[str] = None
    telegram_preview_base64: Optional[str] = None
    loop_telegram_preview_base64: Optional[str] = None
    code_snippet: str
    detail: Optional[str] = None

logger = logging.getLogger(__name__)

def _fetch_and_detect(url: str, service: AutoCalibrationService):
    if not url:
        return None, None, None
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, None, None
            
        image_data = resp.content
        if not image_data or len(image_data) < 100:
            return None, None, None
            
        from PIL import Image, ImageSequence
        import io
        
        pil_img = Image.open(io.BytesIO(image_data))
        first_frame = next(ImageSequence.Iterator(pil_img))
        img = np.array(first_frame.copy().convert("RGB"))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        max_dim = 800
        h, w = img.shape[:2]
        if h > max_dim or w > max_dim:
            scale = max_dim / float(max(h, w))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        circle = service.detect_radar_circle(img)
        crop = None
        if circle:
            crop = service.calculate_crops(img.shape, circle)
        return img, crop, circle
    except Exception as e:
        logger.error(f"[preview] Error processing {url}: {e}")
        return None, None, None

@router.post("/preview", response_model=RadarPreviewResponse)
async def preview_radar_crop(req: RadarPreviewRequest):
    service = AutoCalibrationService()
    
    static_img, static_crop, static_circle = _fetch_and_detect(req.image_url, service)
    if static_img is None:
        raise HTTPException(status_code=400, detail=f"Failed to fetch or decode static image from {req.image_url}")

    loop_img = None
    loop_circle = None

    if req.loop_gif_url:
        loop_img, loop_crop_auto, loop_circle = _fetch_and_detect(req.loop_gif_url, service)
    else:
        loop_crop_auto = None

    if req.crop_x is not None and req.crop_y is not None and req.crop_width is not None and req.crop_height is not None:
        crop_info = {
            "static_crop_x": req.crop_x,
            "static_crop_y": req.crop_y,
            "static_crop_width": req.crop_width,
            "static_crop_height": req.crop_height,
            "loop_crop_x": req.loop_crop_x if req.loop_crop_x is not None else req.crop_x,
            "loop_crop_y": req.loop_crop_y if req.loop_crop_y is not None else req.crop_y,
            "loop_crop_width": req.loop_crop_width if req.loop_crop_width is not None else req.crop_width,
            "loop_crop_height": req.loop_crop_height if req.loop_crop_height is not None else req.crop_height
        }
        override_cx = req.crop_x + req.crop_width // 2
        override_cy = req.crop_y + req.crop_height // 2
        override_r = min(req.crop_width, req.crop_height) // 2
        static_circle = (override_cx, override_cy, override_r)
    else:
        # Auto-Detect mode
        crop_info = {}
        if static_crop:
            crop_info.update(static_crop)
        else:
            crop_info.update({
                "static_crop_x": 0, "static_crop_y": 0,
                "static_crop_width": static_img.shape[1], "static_crop_height": static_img.shape[0]
            })

        if loop_crop_auto:
            crop_info.update({
                "loop_crop_x": loop_crop_auto["static_crop_x"],
                "loop_crop_y": loop_crop_auto["static_crop_y"],
                "loop_crop_width": loop_crop_auto["static_crop_width"],
                "loop_crop_height": loop_crop_auto["static_crop_height"]
            })
        else:
            crop_info.update({
                "loop_crop_x": crop_info["static_crop_x"],
                "loop_crop_y": crop_info["static_crop_y"],
                "loop_crop_width": crop_info["static_crop_width"],
                "loop_crop_height": crop_info["static_crop_height"]
            })

    loop_shape_str = str(loop_img.shape[:2]) if loop_img is not None else "None"
    logger.info(
        f"[PREVIEW] station={req.code} | static_img_shape={static_img.shape[:2]} (h,w) | loop_img_shape={loop_shape_str} | "
        f"static_circle_detected={static_circle} | crop_info={crop_info}"
    )

    # 1. Full image preview with crop overlay (cyan rectangle + red crosshair + detected circle)
    preview_img = service.draw_crop_preview(
        static_img,
        crop_info["static_crop_x"],
        crop_info["static_crop_y"],
        crop_info["static_crop_width"],
        crop_info["static_crop_height"],
        circle=static_circle
    )
    base64_preview = service.to_base64_jpeg(preview_img)

    # 2. Pure cropped image slice for Telegram simulation card
    cropped_img = service.crop_image(
        static_img,
        crop_info["static_crop_x"],
        crop_info["static_crop_y"],
        crop_info["static_crop_width"],
        crop_info["static_crop_height"]
    )
    base64_telegram_preview = service.to_base64_jpeg(cropped_img)

    base64_loop_preview = None
    base64_loop_telegram = None
    if loop_img is not None:
        loop_prev_img = service.draw_crop_preview(
            loop_img,
            crop_info["loop_crop_x"],
            crop_info["loop_crop_y"],
            crop_info["loop_crop_width"],
            crop_info["loop_crop_height"],
            circle=loop_circle
        )
        base64_loop_preview = service.to_base64_jpeg(loop_prev_img)

        cropped_loop = service.crop_image(
            loop_img,
            crop_info["loop_crop_x"],
            crop_info["loop_crop_y"],
            crop_info["loop_crop_width"],
            crop_info["loop_crop_height"]
        )
        base64_loop_telegram = service.to_base64_jpeg(cropped_loop)

    snippet = service.generate_config_snippet(
        code=req.code,
        name=req.name,
        static_url=req.image_url,
        loop_page_url=req.loop_page_url or "",
        loop_gif_url=req.loop_gif_url or "",
        lat=req.lat,
        lng=req.lng,
        radius_km=req.radius_km,
        crop_info=crop_info
    )

    deg_offset = req.radius_km / 111.0
    calc_bbox = {
        "lat_max": round(req.lat + deg_offset, 2),
        "lng_min": round(req.lng - deg_offset, 2),
        "lat_min": round(req.lat - deg_offset, 2),
        "lng_max": round(req.lng + deg_offset, 2)
    }

    return {
        "code": req.code,
        "name": req.name,
        "circle_detected": static_circle is not None,
        "detected_circle": static_circle,
        "crop_info": crop_info,
        "calculated_bbox": calc_bbox,
        "preview_image_base64": base64_preview,
        "loop_preview_image_base64": base64_loop_preview,
        "telegram_preview_base64": base64_telegram_preview,
        "loop_telegram_preview_base64": base64_loop_telegram,
        "code_snippet": snippet
    }

@router.get("/presets")
async def get_radar_presets():
    """Returns catalog of known TMD radar station presets for Admin quick-select."""
    from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
    return KNOWN_TMD_RADAR_PRESETS

@router.post("/seed")
async def seed_radar_stations_to_db(db=Depends(get_async_db)):
    """Seeds validated TMD radar stations into DB (cleaning unvalidated ones first)."""
    from app.database import engine, Base
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.services.tmd_radar_catalog import KNOWN_TMD_RADAR_PRESETS
    from sqlalchemy import delete
    from app.models import RadarStationModel

    # Delete existing stations to reset to validated list only
    valid_codes = [p["code"] for p in KNOWN_TMD_RADAR_PRESETS]
    await db.execute(delete(RadarStationModel).where(RadarStationModel.code.not_in(valid_codes)))
    await db.commit()

    repo = RadarStationRepository(db)
    count = 0
    for preset in KNOWN_TMD_RADAR_PRESETS:
        await repo.upsert_station(preset)
        count += 1
    radar_registry.invalidate_cache()
    return {"status": "ok", "message": f"Successfully synced DB to {count} validated radar stations."}

@router.get("/stations")
async def list_radar_stations(db=Depends(get_async_db)):
    from app.database import engine, Base
    import app.models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    repo = RadarStationRepository(db)
    stations = await repo.get_all_stations()
    return [
        {
            "code": s.code,
            "name": s.name,
            "static_image_url": s.static_image_url,
            "loop_page_url": s.loop_page_url,
            "loop_gif_url": s.loop_gif_url,
            "center_lat": s.center_lat,
            "center_lng": s.center_lng,
            "radius_km": s.radius_km,
            "bbox": {
                "lat_max": s.lat_max,
                "lng_min": s.lng_min,
                "lat_min": s.lat_min,
                "lng_max": s.lng_max
            },
            "static_crop": {
                "x": s.static_crop_x,
                "y": s.static_crop_y,
                "width": s.static_crop_width,
                "height": s.static_crop_height
            },
            "is_active": bool(s.is_active),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in stations
    ]

@router.post("/stations")
async def save_radar_station(req: RadarStationSaveRequest, db=Depends(get_async_db)):
    repo = RadarStationRepository(db)
    saved = await repo.upsert_station(req.model_dump())
    radar_registry.invalidate_cache()

    # Invalidate in-memory frame cache so next bot request downloads fresh
    # frames re-cropped with the new calibration values just saved to DB
    invalidate_station_memory_cache(req.code)

    # Also wipe Firestore frames for this station so stale frames are gone
    try:
        from app.dependencies import get_repo_context
        async with get_repo_context() as _repo:
            await _repo.set_latest_radar_cache(station_code=req.code, frames=[])
        logger.info(f"[ADMIN] Firestore cache cleared for station={req.code} after calibration update")
    except Exception as _e:
        logger.warning(f"[ADMIN] Could not clear Firestore cache for {req.code}: {_e}")

    return {"status": "ok", "code": saved.code, "message": "Radar station saved successfully to DB."}

@router.patch("/stations/{code}/toggle")
async def toggle_radar_station(code: str, is_active: bool, db=Depends(get_async_db)):
    repo = RadarStationRepository(db)
    updated = await repo.toggle_active(code, is_active)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Radar station {code} not found.")
    radar_registry.invalidate_cache()
    return {"status": "ok", "code": code, "is_active": bool(updated.is_active)}
