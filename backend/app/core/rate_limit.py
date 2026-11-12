import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

MINUTE = 60
DAY = 24 * 60 * 60


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, int], deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: int, now: float | None = None) -> bool:
        """Records a hit and returns False when the key already used up its window."""
        now = time.monotonic() if now is None else now
        hits = self._hits[(key, window)]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def clear(self) -> None:
        self._hits.clear()


chat_limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    """Resolves the caller IP, trusting only the proxy hops we operate (taken from the right)."""
    forwarded = [ip.strip() for ip in request.headers.get("x-forwarded-for", "").split(",") if ip]
    count = settings.TRUSTED_PROXY_COUNT
    if count > 0 and len(forwarded) >= count:
        return forwarded[-count]
    return request.client.host if request.client else "unknown"


def enforce_chat_rate_limit(request: Request) -> None:
    ip = client_ip(request)
    allowed = (
        chat_limiter.hit(ip, settings.CHAT_RATE_LIMIT_PER_MINUTE, MINUTE)
        and chat_limiter.hit(ip, settings.CHAT_RATE_LIMIT_PER_DAY, DAY)
        and chat_limiter.hit("__global__", settings.CHAT_GLOBAL_DAILY_LIMIT, DAY)
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many chat requests. Please try again later.",
            headers={"Retry-After": str(MINUTE)},
        )
