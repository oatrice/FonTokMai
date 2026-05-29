from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import weather

app = FastAPI(
    title="FonMaYang (RainNowcast) API",
    description="Short-term rain prediction API (15-30 mins) with privacy-first and pluggable design.",
    version="1.0.0"
)

app.include_router(weather.router)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
