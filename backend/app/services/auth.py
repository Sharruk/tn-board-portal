from datetime import datetime, timedelta
from typing import Optional
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from app.database.database import get_db
from app.models.models import Admin

bearer_scheme = HTTPBearer()

ACCOUNT_LOCKOUT_THRESHOLD = 5
ACCOUNT_LOCKOUT_MINUTES = 15


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def check_account_lockout(admin: Admin) -> tuple[bool, str]:
    """
    Check whether an admin account is currently locked.
    Returns (is_locked, human-readable message).
    """
    if admin.locked_until and datetime.utcnow() < admin.locked_until:
        remaining = max(1, int((admin.locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
        return True, f"Account locked due to too many failed attempts. Try again in {remaining} minute(s)."
    return False, ""


def record_failed_login(db: Session, admin: Admin) -> None:
    """
    Increment failed login count for an admin.
    Locks the account if the threshold is reached.
    """
    admin.failed_login_count = (admin.failed_login_count or 0) + 1
    if admin.failed_login_count >= ACCOUNT_LOCKOUT_THRESHOLD:
        admin.locked_until = datetime.utcnow() + timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
    try:
        db.commit()
    except Exception:
        db.rollback()


def record_successful_login(db: Session, admin: Admin) -> None:
    """
    Reset lockout state and record last login timestamp.
    Called after every successful authentication.
    """
    admin.failed_login_count = 0
    admin.locked_until = None
    admin.last_login_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin
