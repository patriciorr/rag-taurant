import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


bearer = HTTPBearer(auto_error=False)


def require_menu_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    if not settings.MENU_ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Menu administration is not configured.",
        )
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        settings.MENU_ADMIN_TOKEN.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing menu administration credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
