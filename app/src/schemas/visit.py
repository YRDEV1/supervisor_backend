import decimal
from datetime import datetime
from pydantic import BaseModel, computed_field, field_validator

class VisitResponse(BaseModel):
    client_id: str
    client_code: decimal.Decimal
    client_name: str
    check_in: datetime | None
    check_out: datetime | None
    request_time: datetime

    @field_validator("client_id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def worked_minutes(self) -> int | None:
        if self.check_in is None or self.check_out is None:
            return None
        return int((self.check_out - self.check_in).total_seconds() // 60)

class EntryCountResponse(BaseModel):
    entry_count: int

class IdlePeriodResponse(BaseModel):
    idle_start: datetime
    idle_end: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def idle_minutes(self) -> float:
        return round((self.idle_end - self.idle_start).total_seconds() / 60, 2)
