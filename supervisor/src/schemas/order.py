import decimal
from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, field_validator

class OrderSortDirection(str, Enum):
    NEWEST_FIRST = "newest_first"
    OLDEST_FIRST = "oldest_first"

class OrderResponse(BaseModel):
    order_id: str
    order_number: decimal.Decimal
    order_time: datetime
    client_code: decimal.Decimal
    client_name: str
    status: str

    @field_validator("order_id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class OrderPageResponse(BaseModel):
    """Keyset page. Pass `next_cursor` back as `cursor` for the following page;
    `null` means the last page has been reached."""
    items: List[OrderResponse]
    visited_clients: int = 0
    not_visited_clients: int = 0
    current_revenue: float = 0
    total_order_count: int = 0
    target: float = 0
    next_cursor: str | None

class OrderStatusResponse(BaseModel):
    status: str
    count: int

class OrderProductResponse(BaseModel):
    product_name: str
    quantity: decimal.Decimal
    unit_price: decimal.Decimal
    line_total: decimal.Decimal

    model_config = {"from_attributes": True}

class OrderDetailResponse(OrderResponse):
    is_posted: bool
    client_id: str
    client_phone: str
    branch_name: str
    agent_code: decimal.Decimal
    agent_name: str
    total: decimal.Decimal
    products: List[OrderProductResponse]

    @field_validator("client_id", mode="before")
    @classmethod
    def _format_client_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

class AgentTopProductResponse(BaseModel):
    product_name: str
    quantity: decimal.Decimal
    revenue: decimal.Decimal

    model_config = {"from_attributes": True}

class AgentStatsResponse(BaseModel):
    order_count: int
    total_revenue: decimal.Decimal
    first_order: datetime | None
    last_order: datetime | None
    distinct_clients: int
    top_products: List[AgentTopProductResponse]

class AgentSortBy(str, Enum):
    QUANTITY_SOLD = "quantity_sold"
    REVENUE = "revenue"
    PROFIT = "profit"
    ORDER_COUNT = "order_count"
    DISTINCT_CLIENTS = "distinct_clients"

class AgentRatingResponse(BaseModel):
    id: str
    agent_name: str
    quantity_sold: decimal.Decimal
    revenue: decimal.Decimal
    profit: decimal.Decimal
    order_count: int
    distinct_clients: int

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class AgentRatingPageResponse(BaseModel):
    """Keyset page. Pass `next_cursor` back as `cursor` for the following page;
    `null` means the last page has been reached."""
    items: List[AgentRatingResponse]
    next_cursor: str | None
