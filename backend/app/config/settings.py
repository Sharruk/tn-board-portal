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
    # Example: "http://localhost:5173,http://localhost:5000,https://tn-board-portal.vercel.app"
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:5000,"
        "http://localhost:3000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:5000,"
        "http://127.0.0.1:3000,"
        "https://tn-board-portal.vercel.app"
    )

    # ------------------------------------------------------------------ #
    # Firebase Auth
    # Two mutually exclusive ways to provide the service account:
    #   1. FIREBASE_SERVICE_ACCOUNT_JSON — full JSON string of the SA key
    #      (preferred for Vercel/serverless: set the entire file content as an env var)
    #   2. FIREBASE_SERVICE_ACCOUNT_PATH — filesystem path to the JSON file
    #      (useful for local dev where the file exists on disk)
    # auth.py tries (1) first, then falls back to (2).
    # ------------------------------------------------------------------ #
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""   # full SA JSON as a string
    FIREBASE_SERVICE_ACCOUNT_PATH: str = ""   # path to SA JSON file


    # ------------------------------------------------------------------ #
    # Admin Authorization
    # The single Google account that is authorized to access the admin panel.
    # This is NOT a secret. Authorization is enforced server-side by verifying
    # the Firebase ID token and comparing the decoded email to this value.
    # ------------------------------------------------------------------ #
    ADMIN_EMAIL: str = "hungrylearner786@gmail.com"

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
