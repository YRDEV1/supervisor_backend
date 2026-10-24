import decimal
from datetime import datetime
from pydantic import BaseModel, field_validator

class IncomeExpenseResponse(BaseModel):
    period: datetime
    record_kind: int
    amount: decimal.Decimal
    branch_ref: str
    employee_ref: str

    @field_validator("branch_ref", "employee_ref", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}
