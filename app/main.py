import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.routers import auth, stocks, watchlists
from app.scheduler import start_scheduler, stop_scheduler


API_V1_PREFIX = "/api/v1"


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
app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(stocks.router, prefix=API_V1_PREFIX)
app.include_router(stocks.sync_jobs_router, prefix=API_V1_PREFIX)
app.include_router(watchlists.router, prefix=API_V1_PREFIX)


@app.on_event("startup")
def startup_event():
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


@app.api_route("/api", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def api_not_found(full_path: str = ""):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="API endpoint not found",
    )


# Serve built frontend (SPA fallback)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FRONTEND_DIST = os.path.join(_BASE_DIR, "frontend", "dist")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = os.path.join(_FRONTEND_DIST, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
