import datetime

from fastapi import APIRouter, Depends
from typing import List

from app.src.repositories.product import ProductRepository
from app.src.schemas.product import (
    CategoryResponse, ProductResponse, ProductSalesResponse,
    ProductSalesSummaryItem, SalesSummaryResponse, ProductSortBy,
    SalesGrowthResponse, PeriodComparisonResponse,
)
from app.src.core.auth import require_supervisor
from app.src.core.types import NaiveDatetime

product_router = APIRouter(tags=["Product details"], prefix="/product", dependencies=[Depends(require_supervisor)])

@product_router.get("/categories", summary="Get product categories")
async def get_categories(name: str | None = None, page: int = 1, limit: int = 25,
                          product_repo: ProductRepository = Depends()) -> List[CategoryResponse]:
    return await product_repo.get_categories(page=page, limit=limit, name=name)

@product_router.get("/all", summary="Get products")
async def get_all_products(category_id: str | None = None, page: int = 1, limit: int = 50,
                            product_repo: ProductRepository = Depends()) -> List[ProductResponse]:
    return await product_repo.get_all(page=page, limit=limit,
                                       category_id=bytes.fromhex(category_id) if category_id else None)

@product_router.get("/most-sold", summary="Get most sold products")
async def get_most_sold_products(from_date: NaiveDatetime, to_date: NaiveDatetime, page: int = 1, limit: int = 10,
                                  product_repo: ProductRepository = Depends()) -> List[ProductSalesResponse]:
    return await product_repo.get_most_sold(from_date=from_date, to_date=to_date, page=page, limit=limit)

@product_router.get("/least-sold", summary="Get least sold products")
async def get_least_sold_products(from_date: NaiveDatetime, to_date: NaiveDatetime, page: int = 1, limit: int = 10,
                                   product_repo: ProductRepository = Depends()) -> List[ProductSalesResponse]:
    return await product_repo.get_least_sold(from_date=from_date, to_date=to_date, page=page, limit=limit)

@product_router.get("/sales-summary", summary="Get sales statistics by product")
async def get_sales_summary(branch_id: str, from_date: NaiveDatetime | None = None,
                             to_date: NaiveDatetime | None = None, page: int = 1, limit: int = 10,
                             sort_by: ProductSortBy = ProductSortBy.REVENUE,
                             product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    total_revenue, total_profit, products = await product_repo.get_sales_summary(
        branch_id=bytes.fromhex(branch_id), from_date=from_date, to_date=to_date, page=page, limit=limit,
        sort_by=sort_by)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
    )

@product_router.get("/territory-stats", summary="Get total revenue/profit and product sales by territory")
async def get_territory_stats(territory_id: str, from_time: NaiveDatetime | None = None,
                               to_time: NaiveDatetime | None = None, page: int = 1, limit: int = 10,
                               sort_by: ProductSortBy = ProductSortBy.REVENUE,
                               product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    total_revenue, total_profit, products = await product_repo.get_territory_stats(
        territory_id=bytes.fromhex(territory_id), from_time=from_time, to_time=to_time, page=page, limit=limit,
        sort_by=sort_by)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
    )

@product_router.get("/sales-growth", summary="Get sales growth statistics (day/week/month/year over year comparisons)")
async def get_sales_growth(reference_date: NaiveDatetime | None = None,
                            product_repo: ProductRepository = Depends()) -> SalesGrowthResponse:
    growth = await product_repo.get_sales_growth(reference_date=reference_date or datetime.datetime.now())
    return SalesGrowthResponse(
        daily=PeriodComparisonResponse(**growth["daily"]),
        weekly=PeriodComparisonResponse(**growth["weekly"]),
        monthly=PeriodComparisonResponse(**growth["monthly"]),
        yearly=PeriodComparisonResponse(**growth["yearly"]),
    )

@product_router.get("/client-stats", summary="Get total revenue/profit and product sales by client")
async def get_client_stats(client_id: str, from_time: NaiveDatetime | None = None,
                            to_time: NaiveDatetime | None = None, page: int = 1, limit: int = 10,
                            sort_by: ProductSortBy = ProductSortBy.REVENUE,
                            product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    total_revenue, total_profit, products = await product_repo.get_client_stats(
        client_id=bytes.fromhex(client_id), from_time=from_time, to_time=to_time, page=page, limit=limit,
        sort_by=sort_by)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
    )
