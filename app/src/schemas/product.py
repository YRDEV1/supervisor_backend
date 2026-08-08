import decimal
from enum import Enum
from typing import List
from pydantic import BaseModel, field_validator

class ProductSortBy(str, Enum):
    QUANTITY_SOLD = "quantity_sold"
    REVENUE = "revenue"
    PROFIT = "profit"

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
    total_revenue: decimal.Decimal
    total_profit: decimal.Decimal
    products: List[ProductSalesSummaryItem]

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
