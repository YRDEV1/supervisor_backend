"""Opaque keyset (cursor) pagination helpers.

`LIMIT n OFFSET m` makes Postgres walk and discard every one of the first `m`
rows, so cost grows with page depth - measured on `_document4542`, page 1 is
~10ms while `OFFSET 50000` is ~767ms. A keyset cursor carries the sort key of
the last row instead, turning every page into an index range scan (~0.7ms
regardless of depth).

Cursors are base64url-encoded so callers treat them as opaque strings rather
than building their own, which would couple the frontend to the sort key.
"""

import base64
import binascii
import datetime
import decimal

from fastapi import HTTPException


def _encode_part(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return str(value)


def encode_cursor(*parts: object) -> str:
    raw = "|".join(_encode_part(part) for part in parts)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_parts(cursor: str, expected: int) -> list[str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor")

    parts = raw.split("|")
    if len(parts) != expected:
        raise HTTPException(status_code=400, detail="Invalid cursor")
    return parts


def decode_datetime_id_cursor(cursor: str) -> tuple[datetime.datetime, bytes]:
    """Cursor for `ORDER BY <datetime>, <id>` - the tie-breaker `id` keeps the
    sort total, so rows sharing a timestamp are never skipped or repeated."""
    period, hex_id = _decode_parts(cursor, 2)
    try:
        return datetime.datetime.fromisoformat(period), bytes.fromhex(hex_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cursor")


def decode_decimal_id_cursor(cursor: str) -> tuple[decimal.Decimal, bytes]:
    """Cursor for `ORDER BY <numeric code>, <id>`."""
    code, hex_id = _decode_parts(cursor, 2)
    try:
        return decimal.Decimal(code), bytes.fromhex(hex_id)
    except (decimal.InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor")


def decode_id_cursor(cursor: str) -> bytes:
    """Cursor for `ORDER BY <id>` alone, where the id is already unique."""
    (hex_id,) = _decode_parts(cursor, 1)
    try:
        return bytes.fromhex(hex_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cursor")
