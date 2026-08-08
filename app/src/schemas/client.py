import decimal
from enum import Enum
from pydantic import BaseModel, field_validator

class ClientType(str, Enum):
    AKB = "AKB"
    OKB = "OKB"

class ClientResponse(BaseModel):
    id: str
    code: decimal.Decimal
    client_name: str
    phone: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class ClientDetailResponse(ClientResponse):
    latitude: str
    longitude: str
