import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from agents.src.schemas.common import HexId, Number


class AgentCreationForm(BaseModel):
    supervisor_id: HexId
    agent_name: str

    @field_validator("agent_name")
    @classmethod
    def _strip_agent_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Agent name must not be empty")
        return value


class AgentUpdateForm(BaseModel):
    supervisor_id: HexId | None = None
    agent_name: str | None = None

    @field_validator("agent_name")
    @classmethod
    def _strip_agent_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Agent name must not be empty")
        return value


class AgentListResponse(BaseModel):
    id: int
    supervisor_id: HexId
    supervisor_name: str | None
    agent_name: str
    created_at: datetime.datetime


class AgentInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supervisor_id: HexId
    agent_name: str
    created_at: datetime.datetime


class TopProductResponse(BaseModel):
    product_name: str | None
    quantity: Number
    revenue: Number


class AgentStatsResponse(BaseModel):
    id: HexId
    full_name: str
    code: Number | None
    order_count: int
    total_revenue: Number
    first_order: datetime.datetime | None
    last_order: datetime.datetime | None
    distinct_clients: int
    top_products: list[TopProductResponse]
