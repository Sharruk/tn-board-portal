from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.models import Admin
from app.schemas.schemas import LoginRequest, TokenOut
from app.services.auth import (
    verify_password,
    create_access_token,
    check_account_lockout,
    record_failed_login,
    record_successful_login,
)
from app.services.rate_limit import is_locked, record_failure, record_success
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)

    # 1. IP-level rate limit
    locked, secs = is_locked(ip)
    if locked:
        mins = secs // 60 + 1
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts from this IP. Try again in {mins} minute(s).",
            headers={"Retry-After": str(secs)},
        )

    # 2. Find admin by username OR email (accepts either in the username field)
    identifier = payload.username.strip()
    admin = (
        db.query(Admin).filter(Admin.username == identifier).first()
        or db.query(Admin).filter(Admin.email == identifier).first()
    )

    # 3. Credential check
    if not admin or not verify_password(payload.password, admin.password_hash):
        record_failure(ip)
        if admin:
            record_failed_login(db, admin)
        log_action(
            db,
            action="login_failure",
            admin_id=admin.id if admin else None,
            admin_email=admin.email if admin else identifier,
            details={"identifier": identifier},
            ip_address=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # 4. Account lockout check (stored in DB, survives restarts)
    is_acct_locked, lock_msg = check_account_lockout(admin)
    if is_acct_locked:
        log_action(
            db,
            action="login_blocked",
            admin_id=admin.id,
            admin_email=admin.email or admin.username,
            details={"reason": "account_locked"},
            ip_address=ip,
        )
        raise HTTPException(status_code=423, detail=lock_msg)

    # 5. Success — clear lockout state, update last login
    record_success(ip)
    record_successful_login(db, admin)
    log_action(
        db,
        action="login_success",
        admin_id=admin.id,
        admin_email=admin.email or admin.username,
        ip_address=ip,
    )

    token = create_access_token({"sub": admin.username})
    return TokenOut(access_token=token)
