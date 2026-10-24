from datetime import datetime
from pydantic import BaseModel, field_validator

class SupervisorDetailResponse(BaseModel):
    id: str
    full_name: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class AgentIdentityResponse(BaseModel):
    id: str
    full_name: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class AgentDetailResponse(AgentIdentityResponse):
    default_shift_start: datetime
    default_shift_end: datetime