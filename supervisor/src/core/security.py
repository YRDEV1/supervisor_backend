import asyncio
import datetime

import jwt
from jwt.exceptions import JWTDecodeError
from jwt.utils import b64encode

from supervisor.src.core.config import JWT_SECRET_KEY

ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=1)
REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=3)

ALGORITHM = "HS256"

_jwt_instance = jwt.JWT()
_signing_key = jwt.jwk_from_dict({"kty": "oct", "k": b64encode(JWT_SECRET_KEY.encode("utf-8"))})


class InvalidTokenError(Exception):
    pass


def _encode(payload: dict, expires_delta: datetime.timedelta) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    full_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return _jwt_instance.encode(full_payload, _signing_key, alg=ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return _jwt_instance.decode(token, _signing_key, algorithms={ALGORITHM}, do_time_check=True)
    except JWTDecodeError as exc:
        raise InvalidTokenError(str(exc)) from exc


async def create_access_token(employee_id: bytes, role_id: bytes) -> str:
    payload = {"sub": employee_id.hex(), "role": role_id.hex(), "type": "access"}
    return await asyncio.to_thread(_encode, payload, ACCESS_TOKEN_EXPIRES)


async def create_refresh_token(employee_id: bytes, role_id: bytes) -> str:
    payload = {"sub": employee_id.hex(), "role": role_id.hex(), "type": "refresh"}
    return await asyncio.to_thread(_encode, payload, REFRESH_TOKEN_EXPIRES)


async def decode_token(token: str) -> dict:
    return await asyncio.to_thread(_decode, token)
