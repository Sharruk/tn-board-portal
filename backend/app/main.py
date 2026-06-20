import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import CORS_ORIGINS, UPLOAD_DIR, IS_PRODUCTION, ENVIRONMENT
from app.database.database import Base, engine
from app.models import models  # noqa: F401 — registers all models with Base
from app.api import classes, subjects, papers, auth, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Starting TN Board API — environment: {ENVIRONMENT}")

# Create tables
Base.metadata.create_all(bind=engine)

# Disable interactive API docs in production
app = FastAPI(
    title="TN State Board Learning Platform API",
    description="Backend API for Tamil Nadu State Board question papers and answer keys",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files as static
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
API_PREFIX = "/api/v1"
app.include_router(classes.router, prefix=API_PREFIX)
app.include_router(subjects.router, prefix=API_PREFIX)
app.include_router(papers.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ── Production: serve built React frontend ────────────────────────────────────
# In production the Vite dev server is not running.  FastAPI serves the
# pre-built frontend from frontend/dist/ and handles SPA routing via a
# catch-all that always returns index.html for non-API paths.

_FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "frontend", "dist",
)

if IS_PRODUCTION and os.path.isdir(_FRONTEND_DIST):
    # Serve hashed JS/CSS assets (Vite puts them in assets/)
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND_DIST, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def spa_root():
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str, request: Request):
        """Return index.html for all non-API paths so React Router works."""
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index = os.path.join(_FRONTEND_DIST, "index.html")
        return FileResponse(index)
else:
    @app.get("/", tags=["Health"])
    def root():
        return {"status": "ok", "message": "TN State Board Learning Platform API v1.0 — dev mode"}
