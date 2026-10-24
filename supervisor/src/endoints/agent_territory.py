import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import List

from supervisor.src.repositories.agent_territory import AgentTerritoryRepository
from supervisor.src.schemas.agent_territory import AgentTerritoryResponse
from supervisor.src.repositories.visit import VisitRepository
from supervisor.src.schemas.visit import VisitResponse, EntryCountResponse, IdlePeriodResponse, VisitPageResponse
from supervisor.src.schemas.client import ClientResponse, ClientPageResponse
from supervisor.src.core.cursor import decode_datetime_id_cursor, decode_decimal_id_cursor, encode_cursor
from supervisor.src.repositories.order import OrderRepository
from supervisor.src.schemas.order import (
    AgentStatsResponse, AgentTopProductResponse, AgentRatingResponse, AgentSortBy, AgentRatingPageResponse,
)
from supervisor.src.core.auth import require_supervisor
from supervisor.src.core.types import NaiveDatetime, TASHKENT_TZ
from supervisor.src.tasks.agent_stats_cache import (
    agent_stats_cache_key, cache_covers_limit, get_cached, trigger_refresh,
)
from supervisor.src.core.auth import CurrentUser

agent_territory_router = APIRouter(tags=["Agent"], prefix="/agent", dependencies=[Depends(require_supervisor)])

# The cursor carries whichever aggregate the caller sorted by - that is the
# keyset column, so it changes with sort_by.
_RATING_CURSOR_FIELD = {
    AgentSortBy.QUANTITY_SOLD: "quantity_sold",
    AgentSortBy.REVENUE: "revenue",
    AgentSortBy.PROFIT: "profit",
    AgentSortBy.ORDER_COUNT: "order_count",
    AgentSortBy.DISTINCT_CLIENTS: "distinct_clients",
}

@agent_territory_router.get("/territories", summary="Get agent's territories")
async def get_agent_territories(agent_id: str, agent_territory_repo: AgentTerritoryRepository = Depends()) -> List[AgentTerritoryResponse]:
    return await agent_territory_repo.get_agent_territories(agent_id=bytes.fromhex(agent_id))

@agent_territory_router.get("/visit-history", summary="Get agent's visit history to clients (keyset paginated)")
async def get_agent_visit_history(agent_id: str, from_date: NaiveDatetime, to_date: NaiveDatetime,
                                   client_id: str | None = None, cursor: str | None = None, limit: int = 25,
                                   visit_repo: VisitRepository = Depends()) -> VisitPageResponse:
    rows, has_more = await visit_repo.get_agent_visit_history(
        agent_id=bytes.fromhex(agent_id), from_date=from_date, to_date=to_date, limit=limit,
        client_id=bytes.fromhex(client_id) if client_id else None,
        cursor=decode_datetime_id_cursor(cursor) if cursor else None)
    return VisitPageResponse(
        items=[VisitResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1]["first_seen"], rows[-1]["client_id"]) if has_more and rows else None,
    )

@agent_territory_router.get("/entry-count", summary="Get how many times an agent entered a client")
async def get_entry_count(agent_id: str, client_id: str, from_time: NaiveDatetime, to_time: NaiveDatetime,
                           visit_repo: VisitRepository = Depends()) -> EntryCountResponse:
    entry_count = await visit_repo.get_entry_count(agent_id=bytes.fromhex(agent_id), client_id=bytes.fromhex(client_id),
                                                     from_time=from_time, to_time=to_time)
    return EntryCountResponse(entry_count=entry_count or 0)

@agent_territory_router.get("/not-visited-clients", summary="Get clients an agent hasn't visited recently (keyset paginated)")
async def get_not_visited_clients(agent_id: str, days: int | None = None, custom_date: NaiveDatetime | None = None,
                                   cursor: str | None = None, limit: int = 25,
                                   visit_repo: VisitRepository = Depends()) -> ClientPageResponse:
    if days is None and custom_date is None:
        raise HTTPException(status_code=400, detail="Provide either days or custom_date")
    if days is not None and custom_date is not None:
        raise HTTPException(status_code=400, detail="Provide only one of days or custom_date")

    # Naive Tashkent time - DB columns are naive local time, and a tz-aware
    # value errors against them outright (see supervisor/src/endoints/product.py).
    since = custom_date if custom_date is not None else (
        datetime.datetime.now(TASHKENT_TZ).replace(tzinfo=None) - datetime.timedelta(days=days))
    rows, has_more = await visit_repo.get_not_visited_clients(
        agent_id=bytes.fromhex(agent_id), since=since, limit=limit,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
    return ClientPageResponse(
        items=[ClientResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1].code, rows[-1].id) if has_more and rows else None,
    )

@agent_territory_router.get("/idle-time", summary="Get agent's idle/inactive time on a given date")
async def get_agent_idle_time(agent_id: str, date: datetime.date, threshold_minutes: int = 10,
                               visit_repo: VisitRepository = Depends()) -> List[IdlePeriodResponse]:
    day_start = datetime.datetime.combine(date, datetime.time.min)
    rows = await visit_repo.get_agent_idle_periods(agent_id=bytes.fromhex(agent_id), from_date=day_start,
                                                     to_date=day_start + datetime.timedelta(days=1),
                                                     threshold_minutes=threshold_minutes)
    return [IdlePeriodResponse.model_validate(row) for row in rows]

@agent_territory_router.get("/stats", summary="Get agent statistics")
async def get_agent_stats(agent_id: str, background_tasks: BackgroundTasks, top_products_limit: int = 5,
                           from_time: NaiveDatetime | None = None, to_time: NaiveDatetime | None = None,
                           order_repo: OrderRepository = Depends()) -> AgentStatsResponse:
    agent_id_bytes = bytes.fromhex(agent_id)

    # Only the all-time call (no from_time/to_time) is cached - an explicit
    # date range always computes live, same as sales-growth: caching every
    # possible range combination isn't the goal, the common all-time lookup is.
    #
    # The cache key does NOT include top_products_limit - header stats don't
    # depend on it, and the cached product list covers MAX_CACHED_TOP_PRODUCTS
    # up front so changing the limit (e.g. a frontend "top N" selector) keeps
    # hitting the same cache entry instead of missing on every distinct value.
    cacheable = from_time is None and to_time is None
    if cacheable:
        cached = get_cached(agent_stats_cache_key(agent_id_bytes))
        if cached is not None and cache_covers_limit(cached, top_products_limit):
            cached = {**cached, "top_products": cached["top_products"][:top_products_limit]}
            return AgentStatsResponse(**cached)

    stats, top_products = await order_repo.get_agent_stats_with_top_products(
        agent_id=agent_id_bytes, top_products_limit=top_products_limit,
        from_time=from_time, to_time=to_time)

    if cacheable:
        # Deliberately not written here - see supervisor/src/tasks/agent_stats_cache.py.
        # This request's own result never populates Redis; it only asks the
        # Celery worker to compute and cache it, so every write to Redis for
        # this key comes from the worker, not from a request handler.
        # BackgroundTasks defers this until after the response is sent, so a
        # slow/unreachable broker can never add latency to this request.
        background_tasks.add_task(trigger_refresh, agent_id_bytes)

    return AgentStatsResponse(
        order_count=stats.order_count, total_revenue=stats.total_revenue or 0,
        first_order=stats.first_order, last_order=stats.last_order, distinct_clients=stats.distinct_clients,
        top_products=[AgentTopProductResponse.model_validate(row) for row in top_products],
    )

@agent_territory_router.get("/ratings", summary="Get agent ratings by quantity sold, revenue, profit, order count or distinct clients")
async def get_agent_ratings(from_time: NaiveDatetime, to_time: NaiveDatetime, cursor: str | None = None, limit: int = 50,
                             sort_by: AgentSortBy = AgentSortBy.REVENUE,
                             current_user: CurrentUser = Depends(require_supervisor),
                             order_repo: OrderRepository = Depends()) -> AgentRatingPageResponse:
    
    # Get the branch ID of the currently authenticated supervisor
    supervisor_branch_id = current_user.branch_id

    rows, has_more = await order_repo.get_agent_ratings(
        supervisor_branch_id=supervisor_branch_id,
        from_time=from_time, to_time=to_time, limit=limit, sort_by=sort_by,
        cursor=decode_decimal_id_cursor(cursor) if cursor else None)
        
    return AgentRatingPageResponse(
        items=[AgentRatingResponse.model_validate(row) for row in rows],
        next_cursor=encode_cursor(rows[-1][_RATING_CURSOR_FIELD[sort_by]], rows[-1]["id"]) if has_more and rows else None,
    )
