import datetime

from sqlalchemy import func
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.territory import Territory, EXCLUDED_TERRITORY_NAMES
from supervisor.src.models.client import Client
from supervisor.src.models.order import Order
from supervisor.src.models.order_line_item import OrderLineItem
from supervisor.src.schemas.territory import TerritorySortBy
from supervisor.src.repositories.utils import fetch_names

class TerritoryRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all(self, page: int, limit: int, territory_ids: list[bytes], order_by: TerritorySortBy | None = None,
                       from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None):
        # territory_ids is the supervisor's direct, authoritative assignment
        # (see DATA/SUPERVISOR_TERRITORY.md via
        # EmployeeRepository.get_supervisor_territory_ids) - not a
        # branch/visit-pooled proxy, which silently mixes together every
        # supervisor sharing a branch.
        if not territory_ids:
            return []

        if order_by is None:
            query = select(Territory.id, Territory.code, Territory.territory_name).where(
                Territory.id.in_(territory_ids), Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES))
            query = query.order_by(Territory.id).limit(limit).offset((page - 1) * limit)
            execution = await self.session.execute(query)
            return execution.all()

        line_items = select(
            OrderLineItem.sale_total,
            OrderLineItem.cost_total,
            Order.client_ref.label("client_ref"),
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref)
        if from_time is not None and to_time is not None:
            line_items = line_items.where(Order.date_time >= from_time, Order.date_time < to_time)
        line_items = line_items.subquery()

        revenue = func.coalesce(func.sum(line_items.c.sale_total), 0).label("revenue")
        profit = func.coalesce(func.sum(line_items.c.sale_total - line_items.c.cost_total), 0).label("profit")
        sort_column = revenue if order_by == TerritorySortBy.REVENUE else profit

        query = select(
            Territory.id,
            Territory.code,
            revenue,
            profit,
        ).select_from(Territory).outerjoin(
            Client, Client.territory_ref == Territory.id
        ).outerjoin(
            line_items, line_items.c.client_ref == Client.id
        ).where(
            Territory.id.in_(territory_ids), Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES)
        ).group_by(Territory.id, Territory.code).order_by(sort_column.desc())
        query = query.limit(limit).offset((page - 1) * limit)
        rows = (await self.session.execute(query)).all()

        names = await fetch_names(self.session, Territory.id, Territory.territory_name,
                                   [row.id for row in rows])
        return [
            {
                "id": row.id, "code": row.code, "territory_name": names.get(row.id),
                "revenue": row.revenue, "profit": row.profit,
            }
            for row in rows
        ]
