import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.src.repositories.agent_territory import AgentTerritoryRepository
from app.src.schemas.agent_territory import AgentTerritoryResponse
from app.src.repositories.visit import VisitRepository
from app.src.schemas.visit import VisitResponse, EntryCountResponse, IdlePeriodResponse
from app.src.schemas.client import ClientResponse
from app.src.repositories.order import OrderRepository
from app.src.schemas.order import AgentStatsResponse, AgentTopProductResponse, AgentRatingResponse
from app.src.schemas.product import ProductSortBy
from app.src.core.auth import require_supervisor
from app.src.core.types import NaiveDatetime

agent_territory_router = APIRouter(tags=["Agent"], prefix="/agent", dependencies=[Depends(require_supervisor)])

@agent_territory_router.get("/territories", summary="Get agent's territories")
async def get_agent_territories(agent_id: str, agent_territory_repo: AgentTerritoryRepository = Depends()) -> List[AgentTerritoryResponse]:
    return await agent_territory_repo.get_agent_territories(agent_id=bytes.fromhex(agent_id))

@agent_territory_router.get("/visit-history", summary="Get agent's visit history to clients")
async def get_agent_visit_history(agent_id: str, from_date: NaiveDatetime, to_date: NaiveDatetime,
                                   client_id: str | None = None, page: int = 1, limit: int = 25,
                                   visit_repo: VisitRepository = Depends()) -> List[VisitResponse]:
    return await visit_repo.get_agent_visit_history(agent_id=bytes.fromhex(agent_id), from_date=from_date, to_date=to_date,
                                                      page=page, limit=limit,
                                                      client_id=bytes.fromhex(client_id) if client_id else None)

@agent_territory_router.get("/entry-count", summary="Get how many times an agent entered a client")
async def get_entry_count(agent_id: str, client_id: str, from_time: NaiveDatetime, to_time: NaiveDatetime,
                           visit_repo: VisitRepository = Depends()) -> EntryCountResponse:
    entry_count = await visit_repo.get_entry_count(agent_id=bytes.fromhex(agent_id), client_id=bytes.fromhex(client_id),
                                                     from_time=from_time, to_time=to_time)
    return EntryCountResponse(entry_count=entry_count or 0)

@agent_territory_router.get("/not-visited-clients", summary="Get clients an agent hasn't visited recently")
async def get_not_visited_clients(agent_id: str, days: int | None = None, custom_date: NaiveDatetime | None = None,
                                   page: int = 1, limit: int = 25,
                                   visit_repo: VisitRepository = Depends()) -> List[ClientResponse]:
    if days is None and custom_date is None:
        raise HTTPException(status_code=400, detail="Provide either days or custom_date")
    if days is not None and custom_date is not None:
        raise HTTPException(status_code=400, detail="Provide only one of days or custom_date")

    since = custom_date if custom_date is not None else datetime.datetime.now() - datetime.timedelta(days=days)
    return await visit_repo.get_not_visited_clients(agent_id=bytes.fromhex(agent_id), since=since, page=page, limit=limit)

@agent_territory_router.get("/idle-time", summary="Get agent's idle/inactive time on a given date")
async def get_agent_idle_time(agent_id: str, date: datetime.date, threshold_minutes: int = 10,
                               visit_repo: VisitRepository = Depends()) -> List[IdlePeriodResponse]:
    day_start = datetime.datetime.combine(date, datetime.time.min)
    rows = await visit_repo.get_agent_idle_periods(agent_id=bytes.fromhex(agent_id), from_date=day_start,
                                                     to_date=day_start + datetime.timedelta(days=1),
                                                     threshold_minutes=threshold_minutes)
    return [IdlePeriodResponse.model_validate(row) for row in rows]

@agent_territory_router.get("/stats", summary="Get agent statistics")
async def get_agent_stats(agent_id: str, top_products_limit: int = 5,
                           order_repo: OrderRepository = Depends()) -> AgentStatsResponse:
    agent_id_bytes = bytes.fromhex(agent_id)
    stats = await order_repo.get_agent_stats(agent_id=agent_id_bytes)
    top_products = await order_repo.get_agent_top_products(agent_id=agent_id_bytes, limit=top_products_limit)
    return AgentStatsResponse(
        order_count=stats.order_count, total_revenue=stats.total_revenue or 0,
        first_order=stats.first_order, last_order=stats.last_order, distinct_clients=stats.distinct_clients,
        top_products=[AgentTopProductResponse.model_validate(row) for row in top_products],
    )

@agent_territory_router.get("/ratings", summary="Get agent ratings by quantity sold, revenue or profit")
async def get_agent_ratings(from_time: NaiveDatetime, to_time: NaiveDatetime, page: int = 1, limit: int = 50,
                             sort_by: ProductSortBy = ProductSortBy.REVENUE,
                             order_repo: OrderRepository = Depends()) -> List[AgentRatingResponse]:
    return await order_repo.get_agent_ratings(from_time=from_time, to_time=to_time, page=page, limit=limit,
                                               sort_by=sort_by)
