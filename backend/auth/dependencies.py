from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.auth_service import get_user_by_id, public_user
from auth.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    try:
        user_id = int(subject)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    if user_id <= 0:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    current_user = public_user(user)
    request.state.user_id = current_user["id"]
    request.state.role = current_user["role"]
    return current_user


def require_roles(*allowed_roles: str) -> Callable:
    allowed = {role.upper() for role in allowed_roles}

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user

    return dependency
