"""
TN Board Portal — FastAPI application entry point.

Architecture:
    Route → Service → Repository → Supabase

Startup order:
    1. Load settings from .env
    2. Configure structured logging
    3. Create FastAPI app with lifespan
    4. Register CORS middleware
    5. Mount API v1 router
    6. Register root endpoint
"""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.config.settings import get_settings
from app.schemas.root import RootResponse


# ------------------------------------------------------------------ #
# Logging configuration
# Structured, level-controlled logging. Never use print().
# ------------------------------------------------------------------ #
def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "level": level.upper(),
                "handlers": ["console"],
            },
        }
    )


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Application lifespan
# Runs startup/shutdown logic without using deprecated @app.on_event
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


# ------------------------------------------------------------------ #
# Application factory
# ------------------------------------------------------------------ #
def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "TN Board Portal Backend API. "
            "Serves Tamil Nadu State Board exam papers and study resources."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Global exception handler
    # ------------------------------------------------------------------ #
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        origin = request.headers.get("origin")
        headers = {}
        if origin and origin in settings.cors_origins_list:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"

        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected server error occurred."},
            headers=headers
        )

    # ------------------------------------------------------------------ #
    # CORS middleware
    # Allow the React frontend (local dev + Vercel unified/preview deployments).
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Root endpoint — project metadata
    # ------------------------------------------------------------------ #
    @app.get(
        "/",
        response_model=RootResponse,
        summary="API root",
        tags=["Meta"],
        description="Returns project metadata and available endpoint references.",
    )
    async def root() -> RootResponse:
        return RootResponse(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            docs="/docs",
            health="/health",
            api_v1=settings.API_V1_PREFIX,
        )

    # ------------------------------------------------------------------ #
    # Top-level /health alias
    # Canonical versioned route is GET /api/v1/health.
    # Top-level alias is also exposed at /health.
    # ------------------------------------------------------------------ #
    from app.schemas.health import HealthResponse as _HealthResponse
    from app.services.health_service import get_health as _get_health

    @app.get(
        "/health",
        response_model=_HealthResponse,
        summary="Health check (top-level alias)",
        tags=["Health"],
        description="Top-level health check. Identical to /api/v1/health.",
    )
    async def health_alias() -> _HealthResponse:
        return _get_health()


    # ------------------------------------------------------------------ #
    # Mount versioned API router
    # ------------------------------------------------------------------ #
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    logger.info(
        "App ready — CORS origins: %s",
        settings.cors_origins_list,
    )
    return app


# ------------------------------------------------------------------ #
# ASGI application instance
# uvicorn app.main:app
# ------------------------------------------------------------------ #
app = create_app()
