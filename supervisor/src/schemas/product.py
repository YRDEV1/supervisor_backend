import decimal
from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, field_validator

class ProductSortBy(str, Enum):
    QUANTITY_SOLD = "quantity_sold"
    REVENUE = "revenue"
    PROFIT = "profit"

class SoldStatus(str, Enum):
    MOST = "most"
    LEAST = "least"

class CategoryResponse(BaseModel):
    id: str
    category_name: str
    is_marked_for_deletion: bool
    product_count: int

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class ProductResponse(BaseModel):
    id: str
    product_name: str

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class CategoryPageResponse(BaseModel):
    """Keyset page. Pass `next_cursor` back as `cursor` for the following page;
    `null` means the last page has been reached."""
    items: List[CategoryResponse]
    next_cursor: str | None

class ProductPageResponse(BaseModel):
    """Keyset page. Pass `next_cursor` back as `cursor` for the following page;
    `null` means the last page has been reached."""
    items: List[ProductResponse]
    next_cursor: str | None

class ProductSalesResponse(BaseModel):
    id: str
    product_name: str
    total_quantity: decimal.Decimal
    total_revenue: decimal.Decimal

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class ProductSalesSummaryItem(BaseModel):
    id: str
    product_name: str
    quantity_sold: decimal.Decimal
    revenue: decimal.Decimal
    profit: decimal.Decimal

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

class SalesSummaryResponse(BaseModel):
    """Totals cover the whole filtered set; `products` is one keyset page of it.
    Pass `next_cursor` back as `cursor`; `null` means the last page."""
    total_revenue: decimal.Decimal
    total_profit: decimal.Decimal
    products: List[ProductSalesSummaryItem]
    next_cursor: str | None = None

class ProductSalesPageResponse(BaseModel):
    """Keyset page. Pass `next_cursor` back as `cursor` for the following page;
    `null` means the last page has been reached."""
    items: List[ProductSalesResponse]
    next_cursor: str | None

class PeriodComparisonResponse(BaseModel):
    current_revenue: decimal.Decimal
    previous_revenue: decimal.Decimal
    revenue_growth_percent: decimal.Decimal | None
    current_profit: decimal.Decimal
    previous_profit: decimal.Decimal
    profit_growth_percent: decimal.Decimal | None

class SalesGrowthResponse(BaseModel):
    daily: PeriodComparisonResponse
    weekly: PeriodComparisonResponse
    monthly: PeriodComparisonResponse
    yearly: PeriodComparisonResponse

class SalesTrendGranularity(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class SalesTrendPointResponse(BaseModel):
    """One point in the sales-trend series. `target_revenue` is the dynamic
    requirement for the period AFTER this one, not this point's own target -
    see supervisor_backend_requirements.md section 2.3/12.

    `target_revenue` is the plain sum of each team agent's most recent plan
    amount, minus cumulative actual, divided by remaining periods - 0 when
    no agent on the team has ever filed a plan, not a special null case."""
    label: str
    period_start: datetime
    actual_revenue: decimal.Decimal
    target_revenue: decimal.Decimal

    model_config = {"from_attributes": True}

class BranchPlanAgentResponse(BaseModel):
    """One `ТП` agent's contribution to the branch's monthly plan - their
    most recent posted plan doc dated before the month's end (see
    DATA/SALE_TREND.md's "Monthly plan at branch level" section)."""
    agent_code: decimal.Decimal
    agent_name: str
    plan_amount: decimal.Decimal
    plan_set_at: datetime

    model_config = {"from_attributes": True}

class BranchPlanResponse(BaseModel):
    """The branch's total monthly plan - sum of `agents`, each already the
    latest posted plan-as-of-date for that agent, not a plan dated inside
    the month itself (plans persist until revised)."""
    total_plan: decimal.Decimal
    agents: List[BranchPlanAgentResponse]
