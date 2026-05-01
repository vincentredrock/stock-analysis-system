import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.routers import auth, stocks, watchlists
from app.scheduler import start_scheduler, stop_scheduler


app = FastAPI(
    title=settings.app_name,
    description="Taiwan Stock Market Data Platform with JWT Authentication",
    version="2.0.0",
    debug=settings.debug,
)

# CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(watchlists.router)


@app.on_event("startup")
def startup_event():
    if settings.environment == "test" or not settings.stock_daily_sync_enabled:
        return
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


# Serve built frontend (SPA fallback)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_DIST = os.path.join(_BASE_DIR, "frontend", "dist")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = os.path.join(_FRONTEND_DIST, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
