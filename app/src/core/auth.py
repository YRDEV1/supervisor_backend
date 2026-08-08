from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.src.core.security import InvalidTokenError, decode_token
from app.src.models.employee import ROLE_SUPERVISOR

bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    id: bytes
    role_id: bytes


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = await decode_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized

    if payload.get("type") != "access":
        raise unauthorized

    try:
        employee_id = bytes.fromhex(payload["sub"])
        role_id = bytes.fromhex(payload["role"])
    except (KeyError, ValueError):
        raise unauthorized

    return CurrentUser(id=employee_id, role_id=role_id)


async def require_supervisor(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role_id != ROLE_SUPERVISOR.bytes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor role required")
    return current_user
