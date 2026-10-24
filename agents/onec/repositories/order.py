import datetime

from sqlalchemy import String, cast, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by

from agents.onec.database import ONEC_DB_SESSION
from agents.onec.models.order import Order
from agents.onec.models.order_line_item import OrderLineItem
from agents.onec.models.product import Product


class OrderRepository:
    def __init__(self, db: ONEC_DB_SESSION):
        self.db = db

    async def get_agents_stats(self, agent_ids: list[bytes]):
        if not agent_ids:
            return []
        query = (
            select(
                Order.agent_ref,
                func.count(func.distinct(Order.id)).label("order_count"),
                func.coalesce(func.sum(OrderLineItem.sale_total), 0).label("total_revenue"),
                func.coalesce(func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total), 0).label("profit"),
            )
            .join(OrderLineItem, OrderLineItem.order_ref == Order.id)
            .where(Order.agent_ref.in_(agent_ids))
            .group_by(Order.agent_ref)
        )
        execution = await self.db.execute(query)
        return execution.all()

    async def get_agent_stats(
        self,
        agent_id: bytes,
        top_products_limit: int,
        from_time: datetime.datetime | None,
        to_time: datetime.datetime | None,
    ):
        """Order totals and top products, one query."""
        # Reused twice, so scanned once
        agent_orders = select(Order.id, Order.total, Order.date_time, Order.client_ref).where(
            Order.agent_ref == agent_id
        )
        if from_time is not None:
            agent_orders = agent_orders.where(Order.date_time >= from_time)
        if to_time is not None:
            agent_orders = agent_orders.where(Order.date_time < to_time)
        agent_orders = agent_orders.cte("agent_orders")

        quantity = func.sum(OrderLineItem.quantity).label("quantity")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        top_products = (
            select(OrderLineItem.product_ref, quantity, revenue)
            .select_from(agent_orders)
            .join(OrderLineItem, OrderLineItem.order_ref == agent_orders.c.id)
            .group_by(OrderLineItem.product_ref)
            .order_by(revenue.desc())
            .limit(top_products_limit)
            .cte("top_products")
        )

        top_products_json = (
            select(
                func.json_agg(
                    aggregate_order_by(
                        func.json_build_object(
                            "product_name", cast(Product.full_name, String),
                            "quantity", top_products.c.quantity,
                            "revenue", top_products.c.revenue,
                        ),
                        top_products.c.revenue.desc(),
                    )
                )
            )
            .select_from(top_products)
            .outerjoin(Product, Product.id == top_products.c.product_ref)
            .scalar_subquery()
        )

        header = (
            select(
                func.count().label("order_count"),
                func.coalesce(func.sum(agent_orders.c.total), 0).label("total_revenue"),
                func.min(agent_orders.c.date_time).label("first_order"),
                func.max(agent_orders.c.date_time).label("last_order"),
                func.count(func.distinct(agent_orders.c.client_ref)).label("distinct_clients"),
            )
            .select_from(agent_orders)
            .subquery("header")
        )

        query = select(header, top_products_json.label("top_products")).select_from(header)
        execution = await self.db.execute(query)
        return execution.one()
