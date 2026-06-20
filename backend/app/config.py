import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-secret-in-production-abc123xyz")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
MAX_FILE_SIZE_MB = 50

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
