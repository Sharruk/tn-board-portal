"""
In-memory IP-based rate limiter for the login endpoint.

Policy: 5 failed attempts within 15 minutes → IP locked for 15 minutes.

Note: This is per-process. If you run multiple Gunicorn workers,
each worker has its own store. For multi-worker deployments, use Redis
and replace this module with a redis-py implementation.
"""

import threading
from datetime import datetime, timedelta

WINDOW_MINUTES = 15
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

_store: dict[str, dict] = {}
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.utcnow()


def _get_or_create(ip: str) -> dict:
    if ip not in _store:
        _store[ip] = {"count": 0, "window_start": _now(), "locked_until": None}
    return _store[ip]


def is_locked(ip: str) -> tuple[bool, int]:
    """
    Check if an IP is currently locked out.
    Returns (is_locked, seconds_remaining).
    """
    with _lock:
        entry = _get_or_create(ip)
        if entry["locked_until"] and _now() < entry["locked_until"]:
            remaining = int((entry["locked_until"] - _now()).total_seconds())
            return True, max(remaining, 1)
        return False, 0


def record_failure(ip: str) -> bool:
    """
    Record a failed login attempt for an IP.
    Returns True if the IP just became locked (threshold reached).
    """
    with _lock:
        entry = _get_or_create(ip)
        now = _now()
        # Reset window if it has expired
        if now - entry["window_start"] > timedelta(minutes=WINDOW_MINUTES):
            entry["count"] = 0
            entry["window_start"] = now
            entry["locked_until"] = None
        entry["count"] += 1
        if entry["count"] >= MAX_ATTEMPTS:
            entry["locked_until"] = now + timedelta(minutes=LOCKOUT_MINUTES)
            return True
        return False


def record_success(ip: str) -> None:
    """Clear rate-limit state for an IP after a successful login."""
    with _lock:
        _store.pop(ip, None)
