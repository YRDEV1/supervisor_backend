import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from supervisor.src.repositories.product import ProductRepository
from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.repositories.sales_trend import SalesTrendRepository
from supervisor.src.schemas.product import (
    CategoryResponse, ProductResponse, ProductSalesResponse, ProductSalesPageResponse,
    ProductSalesSummaryItem, SalesSummaryResponse, ProductSortBy, SoldStatus,
    SalesGrowthResponse, PeriodComparisonResponse,
    CategoryPageResponse, ProductPageResponse,
    SalesTrendGranularity, SalesTrendPointResponse,
    BranchPlanResponse, BranchPlanAgentResponse,
)
from supervisor.src.core.auth import require_supervisor, CurrentUser
from supervisor.src.core.cursor import decode_decimal_id_cursor, decode_id_cursor, encode_cursor
from supervisor.src.core.sales_trend import month_bounds
from supervisor.src.core.types import NaiveDatetime, TASHKENT_TZ
from supervisor.src.tasks.sales_growth_cache import (
    get_cached, set_cached, short_cache_key, yearly_cache_key, short_ttl, yearly_ttl,
)

product_router = APIRouter(tags=["Product details"], prefix="/product", dependencies=[Depends(require_supervisor)])

# The cursor must carry whichever aggregate the caller sorted by, since that is
# the keyset column.
_STATS_CURSOR_FIELD = {
    ProductSortBy.QUANTITY_SOLD: "quantity_sold",
    ProductSortBy.REVENUE: "revenue",
    ProductSortBy.PROFIT: "profit",
}

def _stats_cursor(products, has_more: bool, sort_by: ProductSortBy) -> str | None:
    if not has_more or not products:
        return None
    last = products[-1]
    return encode_cursor(last[_STATS_CURSOR_FIELD[sort_by]], last["id"])

@product_router.get("/categories", summary="Get product categories (keyset paginated)")
async def get_categories(name: str | None = None, cursor: str | None = None, limit: int = 25,
                          product_repo: ProductRepository = Depends()) -> CategoryPageResponse:
    rows, has_more = await product_repo.get_categories(
        limit=limit, name=name, cursor=decode_id_cursor(cursor) if cursor else None)
    return CategoryPageResponse(
        items=[CategoryResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1].id) if has_more and rows else None,
    )

@product_router.get("/all", summary="Get products (keyset paginated)")
async def get_all_products(category_id: str | None = None, cursor: str | None = None, limit: int = 50,
                            product_repo: ProductRepository = Depends()) -> ProductPageResponse:
    rows, has_more = await product_repo.get_all(
        limit=limit, category_id=bytes.fromhex(category_id) if category_id else None,
        cursor=decode_id_cursor(cursor) if cursor else None)
    return ProductPageResponse(
        items=[ProductResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1].id) if has_more and rows else None,
    )

@product_router.get("/sold", summary="Get most or least sold products (keyset paginated)")
async def get_sold_products(from_date: NaiveDatetime, to_date: NaiveDatetime, status: SoldStatus = SoldStatus.MOST,
                             cursor: str | None = None, limit: int = 10,
                             product_repo: ProductRepository = Depends()) -> ProductSalesPageResponse:
    items, has_more = await product_repo.get_sold(
        from_date=from_date, to_date=to_date, limit=limit, status=status,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return ProductSalesPageResponse(
        items=[ProductSalesResponse.model_validate(row) for row in items],
        next_cursor=encode_cursor(items[-1]["total_quantity"], items[-1]["id"]) if has_more and items else None,
    )

@product_router.get("/sales-summary", summary="Get sales statistics by product")
async def get_sales_summary(from_date: NaiveDatetime | None = None,
                             to_date: NaiveDatetime | None = None, cursor: str | None = None, limit: int = 10,
                             sort_by: ProductSortBy = ProductSortBy.REVENUE,
                             current_user: CurrentUser = Depends(require_supervisor),
                             employee_repo: EmployeeRepository = Depends(),
                             product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    branch_id = await employee_repo.get_branch_ref(current_user.id)
    if branch_id is None:
        raise HTTPException(status_code=400, detail="Supervisor has no branch assigned")

    total_revenue, total_profit, products, has_more = await product_repo.get_sales_summary(
        branch_id=branch_id, from_date=from_date, to_date=to_date, limit=limit,
        sort_by=sort_by, cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
        next_cursor=_stats_cursor(products, has_more, sort_by),
    )

@product_router.get("/territory-stats", summary="Get total revenue/profit and product sales by territory")
async def get_territory_stats(territory_id: str, from_time: NaiveDatetime | None = None,
                               to_time: NaiveDatetime | None = None, cursor: str | None = None, limit: int = 10,
                               sort_by: ProductSortBy = ProductSortBy.REVENUE,
                               product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    total_revenue, total_profit, products, has_more = await product_repo.get_territory_stats(
        territory_id=bytes.fromhex(territory_id), from_time=from_time, to_time=to_time, limit=limit,
        sort_by=sort_by, cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
        next_cursor=_stats_cursor(products, has_more, sort_by),
    )

@product_router.get("/sales-growth", summary="Get sales growth statistics (day/week/month/year over year comparisons)")
async def get_sales_growth(reference_date: NaiveDatetime | None = None,
                            current_user: CurrentUser = Depends(require_supervisor),
                            employee_repo: EmployeeRepository = Depends(),
                            product_repo: ProductRepository = Depends()) -> SalesGrowthResponse:
    branch_id = await employee_repo.get_branch_ref(current_user.id)
    if branch_id is None:
        raise HTTPException(status_code=400, detail="Supervisor has no branch assigned")

    # The two halves are cached on separate schedules, so they are read - and
    # fall back - independently: a stale yearly key never forces the cheap
    # daily/weekly/monthly buckets to be recomputed, or vice versa.
    #
    # Keys are dated, so an explicit reference_date is cached like any other
    # rather than bypassing Redis. Celery keeps today warm; any other date is
    # computed once on first request and written through here.
    #
    # DB columns are naive local (Tashkent) wall-clock time, same as an
    # explicit reference_date after NaiveDatetime strips its tzinfo - so the
    # "now" fallback must be naive Tashkent time too, not converted to UTC or
    # left tz-aware. Comparing a tz-aware value against `TIMESTAMP WITHOUT
    # TIME ZONE` columns errors outright; this was the "reference_date near
    # today returns all zeros" bug from DATA/SALE_TREND.md.
    now = datetime.datetime.now(TASHKENT_TZ).replace(tzinfo=None)
    at = reference_date or now

    short_key = short_cache_key(branch_id, at.date())
    short = get_cached(short_key)
    if short is None:
        short = await product_repo.get_short_sales_growth(reference_date=at, branch_id=branch_id)
        set_cached(short_key, short, short_ttl(at, now))

    yearly_key = yearly_cache_key(branch_id, at.year)
    yearly = get_cached(yearly_key)
    if yearly is None:
        yearly = await product_repo.get_yearly_sales_growth(reference_date=at, branch_id=branch_id)
        set_cached(yearly_key, yearly, yearly_ttl(at, now))

    return SalesGrowthResponse(
        daily=PeriodComparisonResponse(**short["daily"]),
        weekly=PeriodComparisonResponse(**short["weekly"]),
        monthly=PeriodComparisonResponse(**short["monthly"]),
        yearly=PeriodComparisonResponse(**yearly),
    )

@product_router.get("/sales-trend", summary="Get sales trend time series (actual vs dynamic plan target) for the supervisor's team")
async def get_sales_trend(granularity: SalesTrendGranularity, reference_date: NaiveDatetime | None = None,
                           current_user: CurrentUser = Depends(require_supervisor),
                           employee_repo: EmployeeRepository = Depends(),
                           sales_trend_repo: SalesTrendRepository = Depends()) -> List[SalesTrendPointResponse]:
    agent_ids = await employee_repo.get_supervisor_agent_ids(current_user.id)
    at = (reference_date or datetime.datetime.now(TASHKENT_TZ)).date()

    if granularity == SalesTrendGranularity.DAILY:
        shift = await employee_repo.get_shift(current_user.id)
        # Fallback to a conventional 09:00-18:00 window if the supervisor's
        # own shift-time template row is missing/degenerate.
        shift_start = shift.default_shift_start.time() if shift else datetime.time(9, 0)
        shift_end = shift.default_shift_end.time() if shift else datetime.time(18, 0)
        points = await sales_trend_repo.get_daily_trend(
            agent_ids, at, shift_start, shift_end, branch_id=current_user.branch_id)
    elif granularity == SalesTrendGranularity.WEEKLY:
        points = await sales_trend_repo.get_weekly_trend(agent_ids, at, branch_id=current_user.branch_id)
    elif granularity == SalesTrendGranularity.MONTHLY:
        points = await sales_trend_repo.get_monthly_trend(agent_ids, at, branch_id=current_user.branch_id)
    else:
        points = await sales_trend_repo.get_yearly_trend(agent_ids, at, branch_id=current_user.branch_id)

    return [SalesTrendPointResponse.model_validate(p) for p in points]

@product_router.get("/branch-plan", summary="Get the supervisor's branch's total monthly plan, broken down by agent")
async def get_branch_plan(reference_date: NaiveDatetime | None = None,
                           current_user: CurrentUser = Depends(require_supervisor),
                           sales_trend_repo: SalesTrendRepository = Depends()) -> BranchPlanResponse:
    at = (reference_date or datetime.datetime.now(TASHKENT_TZ)).date()
    _, month_end = month_bounds(at)

    total_plan = await sales_trend_repo.get_branch_monthly_plan(current_user.branch_id, month_end)
    agents = await sales_trend_repo.get_branch_plan_breakdown(current_user.branch_id, month_end)
    return BranchPlanResponse(
        total_plan=total_plan,
        agents=[BranchPlanAgentResponse.model_validate(a) for a in agents],
    )

@product_router.get("/client-stats", summary="Get total revenue/profit and product sales by client")
async def get_client_stats(client_id: str, from_time: NaiveDatetime | None = None,
                            to_time: NaiveDatetime | None = None, cursor: str | None = None, limit: int = 10,
                            sort_by: ProductSortBy = ProductSortBy.REVENUE,
                            product_repo: ProductRepository = Depends()) -> SalesSummaryResponse:
    total_revenue, total_profit, products, has_more = await product_repo.get_client_stats(
        client_id=bytes.fromhex(client_id), from_time=from_time, to_time=to_time, limit=limit,
        sort_by=sort_by, cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return SalesSummaryResponse(
        total_revenue=total_revenue, total_profit=total_profit,
        products=[ProductSalesSummaryItem.model_validate(row) for row in products],
        next_cursor=_stats_cursor(products, has_more, sort_by),
    )
