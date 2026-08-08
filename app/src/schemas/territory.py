import decimal
from enum import Enum
from pydantic import BaseModel, field_validator

class TerritorySortBy(str, Enum):
    REVENUE = "revenue"
    PROFIT = "profit"

class TerritoriesResponse(BaseModel):
    id: str
    code: decimal.Decimal
    territory_name: str
    revenue: decimal.Decimal | None = None
    profit: decimal.Decimal | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}
