import decimal
from datetime import datetime
from pydantic import BaseModel, field_validator

class SupervisorsResponse(BaseModel):
    id: str
    code: decimal.Decimal
    full_name: str
    phone: str | None
    login: str | None
    password: str | None

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class SupervisorDetailResponse(BaseModel):
    id: str
    full_name: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class SupervisorAgentsResponse(BaseModel):
    id: str
    full_name: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class AgentDetailResponse(SupervisorAgentsResponse):
    default_shift_start: datetime
    default_shift_end: datetime