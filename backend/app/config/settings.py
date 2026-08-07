"""
Central application configuration.

All values are read from environment variables (or a .env file at backend/.env).
Never hardcode secrets — always use .env.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required variables must exist in the environment or .env file.
    Optional variables have safe defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application identity
    # ------------------------------------------------------------------ #
    APP_NAME: str = "TN Board Portal API"
    APP_VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    LOG_LEVEL: str = "INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL

    # ------------------------------------------------------------------ #
    # Supabase
    # ------------------------------------------------------------------ #
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Optional — only needed for admin ops

    # ------------------------------------------------------------------ #
    # CORS
    # Comma-separated list of allowed origins.
    # Example: "http://localhost:5173,https://tn-board-portal.vercel.app"
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:3000"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS as a parsed Python list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ------------------------------------------------------------------ #
    # Backend self-reference (for future inter-service calls)
    # ------------------------------------------------------------------ #
    BACKEND_URL: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings singleton.

    Using lru_cache ensures the .env file is read only once per process.
    Call get_settings() anywhere you need configuration.
    """
    return Settings()
