from collections import defaultdict
from datetime import datetime, timezone
from fastapi import Request, HTTPException

try:
    from app.config import settings as app_config
except Exception:
    app_config = None


def _get(name: str, default):
    try:
        return getattr(app_config, name, default)
    except Exception:
        return default


AUTH_RATE_LIMIT = _get("AUTH_RATE_LIMIT", 5)
OTP_RATE_LIMIT = _get("OTP_RATE_LIMIT", 3)
RATE_WINDOW_SECONDS = _get("RATE_WINDOW_SECONDS", 15 * 60)
LOGIN_LOCKOUT_AFTER = _get("LOGIN_LOCKOUT_AFTER", 5)
LOGIN_LOCKOUT_SECONDS = _get("LOGIN_LOCKOUT_SECONDS", 15 * 60)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[datetime]] = defaultdict(list)
        self._lockouts: dict[str, datetime] = {}

    def _prune(self, key: str) -> None:
        cutoff = datetime.fromtimestamp(_now().timestamp() - RATE_WINDOW_SECONDS, tz=timezone.utc)
        self._buckets[key] = [ts for ts in self._buckets[key] if ts > cutoff]
        if not self._buckets[key]:
            self._buckets.pop(key, None)

    def allow(self, key: str, limit: int) -> tuple[bool, dict]:
        self._prune(key)
        count = len(self._buckets[key])
        allowed = count < limit
        remaining = max(0, limit - count - (1 if allowed else 0))
        reset_ts = int(_now().timestamp()) + RATE_WINDOW_SECONDS
        meta = {"limit": limit, "remaining": remaining, "reset": reset_ts}
        if allowed:
            self._buckets[key].append(_now())
        return allowed, meta

    def record_failure(self, key: str) -> None:
        self._buckets.setdefault(key, []).append(_now())
        if len(self._buckets.get(key, [])) >= LOGIN_LOCKOUT_AFTER:
            self._lockouts[key] = datetime.fromtimestamp(
                _now().timestamp() + LOGIN_LOCKOUT_SECONDS, tz=timezone.utc
            )

    def clear(self, key: str) -> None:
        self._buckets.pop(key, None)
        self._lockouts.pop(key, None)

    def locked(self, key: str) -> bool:
        until = self._lockouts.get(key)
        return bool(until and _now() < until)

    def lockout_remaining(self, key: str) -> int | None:
        until = self._lockouts.get(key)
        if not until or _now() >= until:
            return None
        return int((until - _now()).total_seconds()) + 1


rate_limiter = RateLimiter()


def _enforce_rate(key: str, limit: int) -> dict:
    allowed, meta = rate_limiter.allow(key, limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {RATE_WINDOW_SECONDS} seconds.",
            headers={"Retry-After": str(RATE_WINDOW_SECONDS)},
        )
    return meta


def rate_limit_auth(request: Request) -> dict:
    return _enforce_rate(f"auth:{_ip(request)}", AUTH_RATE_LIMIT)


def rate_limit_otp(request: Request) -> dict:
    return _enforce_rate(f"otp:{_ip(request)}", OTP_RATE_LIMIT)


def login_throttle(request: Request) -> str:
    key = f"login:{_ip(request)}"
    if rate_limiter.locked(key):
        remaining = rate_limiter.lockout_remaining(key)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )
    return key
