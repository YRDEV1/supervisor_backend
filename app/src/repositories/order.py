import datetime

from sqlalchemy import func
from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.order import Order, get_order_status_filter
from app.src.models.client import Client
from app.src.models.branch import Branch
from app.src.models.employee import Employee
from app.src.models.order_line_item import OrderLineItem
from app.src.models.product import Product
from app.src.models.visit import Visit
from app.src.schemas.product import ProductSortBy
from app.src.repositories.utils import fetch_names
from app.src.schemas.order import OrderSortDirection

class OrderRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all(self, from_date: datetime.datetime, to_date: datetime.datetime, page: int, limit: int,
                       status: str | None = None, supervisor_id: bytes | None = None,
                       sort_direction: OrderSortDirection = OrderSortDirection.NEWEST_FIRST):
        query = select(
            Order.id.label("order_id"),
            Order.number.label("order_number"),
            Order.date_time.label("order_time"),
            Client.code.label("client_code"),
            Client.full_name.label("client_name"),
            Order.status_ref,
        ).select_from(Order).join(Client, Client.id == Order.client_ref).where(
            Order.date_time >= from_date, Order.date_time < to_date
        )
        if status is not None:
            query = query.where(get_order_status_filter(status))
        if supervisor_id is not None:
            supervisor_branch = select(Employee.branch_ref).where(Employee.id == supervisor_id).scalar_subquery()
            agent_ids = select(Visit.agent_ref).where(Visit.supervisor_individual_ref == supervisor_branch).distinct()
            query = query.where(Order.agent_ref.in_(agent_ids))
        order_by_column = Order.date_time.desc() if sort_direction == OrderSortDirection.NEWEST_FIRST else Order.date_time.asc()
        query = query.order_by(order_by_column).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_status_counts(self):
        query = select(Order.status_ref, func.count().label("count")).group_by(Order.status_ref)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_by_id(self, order_id: bytes):
        query = select(
            Order.id.label("order_id"),
            Order.number.label("order_number"),
            Order.date_time.label("order_time"),
            Order.is_posted,
            Order.total,
            Order.status_ref,
            Client.id.label("client_id"),
            Client.code.label("client_code"),
            Client.full_name.label("client_name"),
            Client.phone.label("client_phone"),
            Branch.full_name.label("branch_name"),
            Employee.code.label("agent_code"),
            Employee.full_name.label("agent_name"),
        ).select_from(Order).join(Client, Client.id == Order.client_ref).join(
            Branch, Branch.id == Order.branch_ref
        ).join(Employee, Employee.id == Order.agent_ref).where(Order.id == order_id)
        execution = await self.session.execute(query)
        return execution.one_or_none()

    async def get_products(self, order_id: bytes):
        query = select(
            Product.full_name.label("product_name"),
            OrderLineItem.quantity,
            (OrderLineItem.sale_total / func.nullif(OrderLineItem.quantity, 0)).label("unit_price"),
            OrderLineItem.sale_total.label("line_total"),
        ).select_from(OrderLineItem).join(Product, Product.id == OrderLineItem.product_ref).where(
            OrderLineItem.order_ref == order_id
        )
        execution = await self.session.execute(query)
        return execution.all()

    async def get_agent_stats(self, agent_id: bytes):
        query = select(
            func.count().label("order_count"),
            func.sum(Order.total).label("total_revenue"),
            func.min(Order.date_time).label("first_order"),
            func.max(Order.date_time).label("last_order"),
            func.count(func.distinct(Order.client_ref)).label("distinct_clients"),
        ).where(Order.agent_ref == agent_id)
        execution = await self.session.execute(query)
        return execution.one()

    async def get_agent_top_products(self, agent_id: bytes, limit: int):
        quantity = func.sum(OrderLineItem.quantity).label("quantity")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        query = select(
            OrderLineItem.product_ref,
            quantity,
            revenue,
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
            Order.agent_ref == agent_id
        ).group_by(OrderLineItem.product_ref).order_by(revenue.desc()).limit(limit)
        rows = (await self.session.execute(query)).all()

        names = await fetch_names(self.session, Product.id, Product.full_name,
                                   [row.product_ref for row in rows])
        return [
            {"product_name": names.get(row.product_ref), "quantity": row.quantity, "revenue": row.revenue}
            for row in rows
        ]

    async def get_agent_ratings(self, from_time: datetime.datetime, to_time: datetime.datetime, page: int, limit: int,
                                 sort_by: ProductSortBy = ProductSortBy.REVENUE):
        quantity_sold = func.sum(OrderLineItem.quantity).label("quantity_sold")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        profit = func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("profit")
        sort_column = {
            ProductSortBy.QUANTITY_SOLD: quantity_sold,
            ProductSortBy.REVENUE: revenue,
            ProductSortBy.PROFIT: profit,
        }[sort_by]

        query = select(
            Order.agent_ref,
            quantity_sold,
            revenue,
            profit,
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
            Order.date_time >= from_time, Order.date_time < to_time
        ).group_by(Order.agent_ref).order_by(sort_column.desc())
        query = query.limit(limit).offset((page - 1) * limit)
        rows = (await self.session.execute(query)).all()

        names = await fetch_names(self.session, Employee.id, Employee.full_name,
                                   [row.agent_ref for row in rows])
        return [
            {
                "id": row.agent_ref, "agent_name": names.get(row.agent_ref),
                "quantity_sold": row.quantity_sold, "revenue": row.revenue, "profit": row.profit,
            }
            for row in rows
        ]
