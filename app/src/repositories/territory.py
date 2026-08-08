import datetime

from sqlalchemy import func
from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.territory import Territory
from app.src.models.client import Client
from app.src.models.order import Order
from app.src.models.order_line_item import OrderLineItem
from app.src.schemas.territory import TerritorySortBy

class TerritoryRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all(self, page: int, limit: int, order_by: TerritorySortBy | None = None,
                       from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None):
        if order_by is None:
            query = select(Territory.id, Territory.code, Territory.territory_name)
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
            Territory.territory_name,
            revenue,
            profit,
        ).select_from(Territory).outerjoin(
            Client, Client.territory_ref == Territory.id
        ).outerjoin(
            line_items, line_items.c.client_ref == Client.id
        ).group_by(Territory.id, Territory.code, Territory.territory_name).order_by(sort_column.desc())
        query = query.limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()
