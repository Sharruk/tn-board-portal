import os
import logging
import warnings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Runtime environment ───────────────────────────────────────────────────────

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# ── Database ──────────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Add it to your .env file or environment secrets."
    )

# ── Authentication ────────────────────────────────────────────────────────────

_INSECURE_DEFAULT_SECRET = "change-this-secret-in-production-abc123xyz"

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _INSECURE_DEFAULT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

if JWT_SECRET_KEY == _INSECURE_DEFAULT_SECRET:
    if IS_PRODUCTION:
        raise RuntimeError(
            "JWT_SECRET_KEY is still the insecure default value. "
            "Set a strong random secret in your environment before deploying.\n"
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    else:
        warnings.warn(
            "⚠️  JWT_SECRET_KEY is using the insecure default. "
            "Set JWT_SECRET_KEY in your .env before deploying to production.",
            stacklevel=2,
        )

if len(JWT_SECRET_KEY) < 32 and IS_PRODUCTION:
    raise RuntimeError(
        "JWT_SECRET_KEY is too short. Use at least 32 characters in production."
    )

# ── CORS ──────────────────────────────────────────────────────────────────────

_cors_raw = os.environ.get("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

if "*" in CORS_ORIGINS and IS_PRODUCTION:
    raise RuntimeError(
        "CORS_ORIGINS is set to '*' in production. "
        "Set it to the exact frontend URL(s) in your environment."
    )

# ── File storage ──────────────────────────────────────────────────────────────

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").lower()

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "50"))

if STORAGE_BACKEND == "local" and IS_PRODUCTION:
    warnings.warn(
        "⚠️  STORAGE_BACKEND=local in production. "
        "Uploaded PDFs will be lost when the server restarts or redeploys. "
        "Switch to STORAGE_BACKEND=s3 or STORAGE_BACKEND=supabase.",
        stacklevel=2,
    )
