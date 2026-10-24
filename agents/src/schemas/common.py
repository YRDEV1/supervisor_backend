import decimal
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


def _hex_to_bytes(value):
    if isinstance(value, str):
        try:
            value = bytes.fromhex(value)
        except ValueError:
            raise ValueError("Invalid ID format")
    if isinstance(value, bytes) and len(value) != 16:
        raise ValueError("Invalid ID format")
    return value


def _decimal_to_number(value: decimal.Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


# 16 bytes shown as hex
HexId = Annotated[
    bytes,
    BeforeValidator(_hex_to_bytes),
    PlainSerializer(lambda value: value.hex(), return_type=str, when_used="json"),
]

# Decimal shown as plain number
Number = Annotated[
    decimal.Decimal,
    PlainSerializer(_decimal_to_number, return_type=int | float, when_used="json"),
]
