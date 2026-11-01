"""In-memory rate limiting and client IP extraction utilities (Module 11A).

Note: In-memory sliding window rate limiting is per-process and best-effort;
the database-backed user lockout is the authoritative control across processes.
"""
from collections import defaultdict
from datetime import datetime, timezone
import threading
from typing import Dict, List

from fastapi import Request
from starlette import status

from app.core.config import get_settings
from app.core.exceptions import AppHTTPException


def get_client_ip(request: Request) -> str:
    """Extract client IP address safely respecting TRUSTED_PROXY_COUNT.

    Only trusts X-Forwarded-For if TRUSTED_PROXY_COUNT > 0, taking the right-most-minus-N
    entry to prevent client header spoofing. Defaults to request.client.host.
    """
    settings = get_settings()
    if settings.TRUSTED_PROXY_COUNT > 0:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if len(parts) >= settings.TRUSTED_PROXY_COUNT:
                return parts[-settings.TRUSTED_PROXY_COUNT]
    return request.client.host if request.client else "127.0.0.1"


class InMemoryRateLimiter:
    """Sliding-window in-memory request counter per IP."""

    def __init__(self):
        self._lock = threading.Lock()
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, client_ip: str, limit_per_minute: int) -> None:
        """Check if client_ip exceeded limit_per_minute. Raises 429 if tripped."""
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - 60.0

        with self._lock:
            # Prune timestamps older than 60 seconds
            timestamps = [t for t in self._history[client_ip] if t > window_start]
            if len(timestamps) >= limit_per_minute:
                # Oldest timestamp determines retry after
                oldest = timestamps[0]
                retry_after = max(1, int(60.0 - (now - oldest)))
                self._history[client_ip] = timestamps
                raise AppHTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed attempts. Try again later.",
                    code="too_many_attempts",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)
            self._history[client_ip] = timestamps

    def reset(self) -> None:
        """Clear all rate limit state (used for testing)."""
        with self._lock:
            self._history.clear()


# Global login rate limiter singleton
login_rate_limiter = InMemoryRateLimiter()

