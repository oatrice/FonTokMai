from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.routers import weather, webhook

from contextlib import asynccontextmanager
from app.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="FonMaYang (RainNowcast) API",
    description="Short-term rain prediction API (15-30 mins) with privacy-first and pluggable design.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(weather.router)
app.include_router(webhook.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
