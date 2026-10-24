from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy.future import select
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supervisor.src.models.employee import Employee

from supervisor.src.core.security import InvalidTokenError, decode_token
from supervisor.src.models.employee import ROLE_SUPERVISOR
from supervisor.src.core.database import get_db

bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    id: bytes
    role_id: bytes
    branch_id: bytes


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
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

    # Fetch the branch_id from the database
    result = await session.execute(
        select(Employee.branch_ref).where(Employee.id == employee_id)
    )
    branch_id = result.scalar_one_or_none()
    
    if branch_id is None:
        raise unauthorized  # Employee not found or has no branch assigned

    return CurrentUser(id=employee_id, role_id=role_id, branch_id=branch_id)


async def require_supervisor(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role_id != ROLE_SUPERVISOR.bytes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor role required")
    return current_user
