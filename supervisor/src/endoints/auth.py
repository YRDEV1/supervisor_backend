from fastapi import APIRouter, Depends, HTTPException, status

from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from supervisor.src.core.security import create_access_token, create_refresh_token, decode_token, InvalidTokenError

auth_router = APIRouter(tags=["Auth"], prefix="/auth")

@auth_router.post("/login", summary="Log in with employee login/password")
async def login(payload: LoginRequest, employee_repo: EmployeeRepository = Depends()) -> TokenResponse:
    employee = await employee_repo.get_by_credentials(login=payload.login, password=payload.password)
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")

    access_token = await create_access_token(employee_id=employee.id, role_id=employee.parent_id)
    refresh_token = await create_refresh_token(employee_id=employee.id, role_id=employee.parent_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@auth_router.post("/refresh", summary="Exchange a refresh token for a new token pair")
async def refresh(payload: RefreshRequest) -> TokenResponse:
    try:
        claims = await decode_token(payload.refresh_token)
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    try:
        employee_id = bytes.fromhex(claims["sub"])
        role_id = bytes.fromhex(claims["role"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    access_token = await create_access_token(employee_id=employee_id, role_id=role_id)
    new_refresh_token = await create_refresh_token(employee_id=employee_id, role_id=role_id)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
