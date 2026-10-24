import datetime
import decimal

from sqlalchemy import func, text, tuple_, union
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.order import Order, get_order_status_filter
from supervisor.src.models.client import Client
from supervisor.src.models.branch import Branch
from supervisor.src.models.employee import Employee
from supervisor.src.models.order_line_item import OrderLineItem
from supervisor.src.models.product import Product
from supervisor.src.models.visit import Visit
from supervisor.src.repositories.utils import fetch_names
from supervisor.src.schemas.order import OrderSortDirection, AgentSortBy

EXCLUDED_AGENT_ID = bytes.fromhex("a738005056070e0911f0360728fc9c83")

class OrderRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all(
        self,
        from_date: datetime.datetime | None,
        to_date: datetime.datetime | None,
        limit: int,
        cursor: tuple[datetime.datetime, bytes] | None = None,
        status: str | None = None,
        agent_ids: list[bytes] | None = None,
        sort_direction: OrderSortDirection = OrderSortDirection.NEWEST_FIRST,
    ):
        newest_first = sort_direction == OrderSortDirection.NEWEST_FIRST

        # 1. Main query for rows (No func.count or group_by needed)
        query = (
            select(
                Order.id.label("order_id"),
                Order.number.label("order_number"),
                Order.total.label("total_amount"),
                Order.date_time.label("order_time"),
                Client.code.label("client_code"),
                Client.full_name.label("client_name"),
                Order.status_ref,
            )
            .select_from(Order)
            .join(Client, Client.id == Order.client_ref)
        )

        if from_date is not None:
            query = query.where(Order.date_time >= from_date)
        if to_date is not None:
            query = query.where(Order.date_time < to_date)
        if status is not None:
            query = query.where(get_order_status_filter(status))
        if agent_ids is not None:
            query = query.where(Order.agent_ref.in_(agent_ids))

        # 2. Revenue query
        revenue_query = select(
            func.coalesce(func.sum(Order.total), 0)
        ).select_from(Order)

        if from_date is not None:
            revenue_query = revenue_query.where(Order.date_time >= from_date)
        if to_date is not None:
            revenue_query = revenue_query.where(Order.date_time < to_date)
        if status is not None:
            revenue_query = revenue_query.where(get_order_status_filter(status))
        if agent_ids is not None:
            revenue_query = revenue_query.where(Order.agent_ref.in_(agent_ids))

        # 3. Total Count query
        count_query = select(func.count(Order.id)).select_from(Order)

        if from_date is not None:
            count_query = count_query.where(Order.date_time >= from_date)
        if to_date is not None:
            count_query = count_query.where(Order.date_time < to_date)
        if status is not None:
            count_query = count_query.where(get_order_status_filter(status))
        if agent_ids is not None:
            count_query = count_query.where(Order.agent_ref.in_(agent_ids))

        total_revenue = (await self.session.execute(revenue_query)).scalar_one()
        total_orders_count = (await self.session.execute(count_query)).scalar_one()

        if cursor is not None:
            row = tuple_(Order.date_time, Order.id)
            after = tuple_(*cursor)
            query = query.where(
                row < after if newest_first else row > after
            )

        query = query.order_by(
            *((Order.date_time.desc(), Order.id.desc()) if newest_first
            else (Order.date_time.asc(), Order.id.asc()))
        )

        rows = (await self.session.execute(query.limit(limit + 1))).all()

        return rows[:limit], len(rows) > limit, total_revenue, total_orders_count

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
        return execution.first()

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

    async def get_cacheable_agent_ids(self) -> list[bytes]:
        """Every agent id that `/agent/stats` could ever be called with.

        Deliberately the full reachable set, not just recently-active agents:
        the frontend gets ids from `/employee/supervisors/agents` (built from
        the visit register), so any agent listed there can be clicked into -
        and an agent the warming sweep skipped is exactly the one that pays a
        slow uncached request. Measured 288 in the visit register, 288 in
        orders, union 289 - each source misses 2 the other has, so both are
        needed.
        """
        query = union(
            select(Visit.agent_ref.label("agent_ref")).distinct(),
            select(Order.agent_ref.label("agent_ref")).distinct(),
        )
        rows = (await self.session.execute(query)).scalars().all()
        return [ref for ref in rows if ref and ref != b"\x00" * 16]

    async def get_agent_stats_with_top_products(self, agent_id: bytes, top_products_limit: int,
                                                  from_time: datetime.datetime | None = None,
                                                  to_time: datetime.datetime | None = None):
        """Header stats + top products in one round trip.

        Split across two queries, each filtered on the unindexed
        `Order.agent_ref`, this cost two full sequential scans of
        `_document4542` (~55ms + ~139ms locally). An index would fix that
        directly, but it's not available here - instead, `agent_orders` is a
        CTE: Postgres materializes it by scanning the order table exactly
        once, and both the header aggregates and the top-products join (via
        the already-indexed `_document4542_vt4599` PK) read from that
        materialization instead of re-filtering the order table. Measured
        ~72ms single round trip for the same agent, roughly half the original
        cost, with no schema change.
        """
        agent_orders = select(
            Order.id.label("order_id"), Order.total, Order.date_time, Order.client_ref,
        ).where(Order.agent_ref == agent_id)
        if from_time is not None:
            agent_orders = agent_orders.where(Order.date_time >= from_time)
        if to_time is not None:
            agent_orders = agent_orders.where(Order.date_time < to_time)
        agent_orders = agent_orders.cte("agent_orders")

        quantity = func.sum(OrderLineItem.quantity).label("quantity")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        top_products = select(
            OrderLineItem.product_ref.label("product_ref"), quantity, revenue,
        ).select_from(agent_orders).join(
            OrderLineItem, OrderLineItem.order_ref == agent_orders.c.order_id
        ).group_by(OrderLineItem.product_ref).order_by(revenue.desc()).limit(top_products_limit).cte("top_products")

        # json_agg packs the top-products rows into a single scalar so they
        # can travel alongside the header aggregates in one result row -
        # that's what keeps this to one round trip instead of two.
        top_products_json = select(
            func.json_agg(aggregate_order_by(
                func.json_build_object(
                    "product_ref", func.encode(top_products.c.product_ref, "hex"),
                    "quantity", top_products.c.quantity,
                    "revenue", top_products.c.revenue,
                ),
                top_products.c.revenue.desc(),
            ))
        ).select_from(top_products).scalar_subquery()

        query = select(
            select(func.count()).select_from(agent_orders).scalar_subquery().label("order_count"),
            select(func.coalesce(func.sum(agent_orders.c.total), 0)).select_from(agent_orders)
                .scalar_subquery().label("total_revenue"),
            select(func.min(agent_orders.c.date_time)).select_from(agent_orders)
                .scalar_subquery().label("first_order"),
            select(func.max(agent_orders.c.date_time)).select_from(agent_orders)
                .scalar_subquery().label("last_order"),
            select(func.count(func.distinct(agent_orders.c.client_ref))).select_from(agent_orders)
                .scalar_subquery().label("distinct_clients"),
            top_products_json.label("top_products_json"),
        )
        row = (await self.session.execute(query)).one()

        # asyncpg already decodes the json_agg result to a Python list/dict.
        top_products_raw = row.top_products_json or []
        product_refs = [bytes.fromhex(item["product_ref"]) for item in top_products_raw]
        names = await fetch_names(self.session, Product.id, Product.full_name, product_refs)
        top_products_list = [
            {
                "product_name": names.get(bytes.fromhex(item["product_ref"])),
                "quantity": item["quantity"], "revenue": item["revenue"],
            }
            for item in top_products_raw
        ]

        return row, top_products_list

    async def get_agent_ratings(self, supervisor_branch_id: bytes, from_time: datetime.datetime, to_time: datetime.datetime, limit: int,
                                    sort_by: AgentSortBy = AgentSortBy.REVENUE,
                                    cursor: tuple[decimal.Decimal, bytes] | None = None):
        quantity_sold = func.sum(OrderLineItem.quantity).label("quantity_sold")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        profit = func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("profit")
        order_count = func.count(func.distinct(Order.id)).label("order_count")
        distinct_clients = func.count(func.distinct(Order.client_ref)).label("distinct_clients")
        
        sort_column = {
            AgentSortBy.QUANTITY_SOLD: quantity_sold,
            AgentSortBy.REVENUE: revenue,
            AgentSortBy.PROFIT: profit,
            AgentSortBy.ORDER_COUNT: order_count,
            AgentSortBy.DISTINCT_CLIENTS: distinct_clients,
        }[sort_by]
        
        sort_expression = {
            AgentSortBy.QUANTITY_SOLD: func.sum(OrderLineItem.quantity),
            AgentSortBy.REVENUE: func.sum(OrderLineItem.sale_total),
            AgentSortBy.PROFIT: func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total),
            AgentSortBy.ORDER_COUNT: func.count(func.distinct(Order.id)),
            AgentSortBy.DISTINCT_CLIENTS: func.count(func.distinct(Order.client_ref)),
        }[sort_by]

        query = select(
            Order.agent_ref,
            quantity_sold,
            revenue,
            profit,
            order_count,
            distinct_clients,
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).join(
            Employee, Employee.id == Order.agent_ref
        ).where(
            Order.date_time >= from_time, 
            Order.date_time < to_time,
            Employee.branch_ref == supervisor_branch_id,
            Order.branch_ref == supervisor_branch_id,
            Order.agent_ref != EXCLUDED_AGENT_ID
        ).group_by(Order.agent_ref)
        
        if cursor is not None:
            query = query.having(tuple_(sort_expression, Order.agent_ref) < tuple_(*cursor))
            
        query = query.order_by(sort_column.desc(), Order.agent_ref.desc()).limit(limit + 1)
        
        await self.session.execute(text("SET LOCAL work_mem = '128MB'"))
        rows = (await self.session.execute(query)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        names = await fetch_names(self.session, Employee.id, Employee.full_name,
                                [row.agent_ref for row in rows])
        return [
            {
                "id": row.agent_ref, "agent_name": names.get(row.agent_ref),
                "quantity_sold": row.quantity_sold, "revenue": row.revenue, "profit": row.profit,
                "order_count": row.order_count, "distinct_clients": row.distinct_clients,
            }
            for row in rows
        ], has_more 