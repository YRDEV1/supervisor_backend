import datetime
import decimal

from sqlalchemy import case, cast, exists, func, String, text, tuple_
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.product import Product, ROOT_PARENT_ID
from supervisor.src.models.order import Order
from supervisor.src.models.order_line_item import OrderLineItem
from supervisor.src.models.client import Client
from supervisor.src.schemas.product import ProductSortBy, SoldStatus
from supervisor.src.repositories.utils import fetch_names

class ProductRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_categories(self, limit: int, name: str | None = None, cursor: bytes | None = None):
        child = aliased(Product)
        query = select(
            Product.id,
            Product.full_name.label("category_name"),
            Product.is_marked_for_deletion,
            select(func.count()).select_from(child).where(child.parent_id == Product.id)
                .scalar_subquery().label("product_count"),
        ).where(
            Product.parent_id == ROOT_PARENT_ID,
            exists(select(1).select_from(child).where(child.parent_id == Product.id)),
        )
        # Name filter runs in Postgres now - the previous version materialised
        # every category (each carrying a correlated COUNT subquery) before
        # slicing in Python.
        if name:
            # Unlike `=`/`!=`, there's no `mvarchar ~~* mvarchar` ILIKE
            # operator at all on this DB export, so ILIKE still needs an
            # explicit text cast even though full_name is typed MVARCHAR.
            query = query.where(cast(Product.full_name, String).ilike(f"%{name}%"))
        if cursor is not None:
            query = query.where(Product.id > cursor)
        query = query.order_by(Product.id).limit(limit + 1)
        rows = (await self.session.execute(query)).all()
        return rows[:limit], len(rows) > limit

    async def get_all(self, limit: int, category_id: bytes | None = None, cursor: bytes | None = None):
        query = select(
            Product.id,
            Product.full_name.label("product_name"),
        )
        if category_id is not None:
            query = query.where(Product.parent_id == category_id)
        if cursor is not None:
            query = query.where(Product.id > cursor)
        query = query.order_by(Product.id).limit(limit + 1)
        rows = (await self.session.execute(query)).all()
        return rows[:limit], len(rows) > limit

    async def _get_sales(self, from_date: datetime.datetime, to_date: datetime.datetime, limit: int,
                          descending: bool, cursor: tuple[decimal.Decimal, bytes] | None = None):
        total_quantity = func.sum(OrderLineItem.quantity).label("total_quantity")
        total_revenue = func.sum(OrderLineItem.sale_total).label("total_revenue")
        query = select(
            OrderLineItem.product_ref,
            total_quantity,
            total_revenue,
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
            Order.date_time >= from_date, Order.date_time < to_date
        ).group_by(OrderLineItem.product_ref)
        # Keyset on an aggregate goes in HAVING, not WHERE - the sort key only
        # exists after grouping. product_ref breaks ties so products sharing a
        # quantity can't be skipped or repeated across pages.
        if cursor is not None:
            key = tuple_(func.sum(OrderLineItem.quantity), OrderLineItem.product_ref)
            after = tuple_(*cursor)
            query = query.having(key < after if descending else key > after)
        query = query.order_by(
            *((total_quantity.desc(), OrderLineItem.product_ref.desc()) if descending
              else (total_quantity.asc(), OrderLineItem.product_ref.asc()))
        ).limit(limit + 1)
        await self.session.execute(text("SET LOCAL work_mem = '128MB'"))
        rows = (await self.session.execute(query)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        names = await fetch_names(self.session, Product.id, Product.full_name,
                                   [row.product_ref for row in rows])
        return [
            {
                "id": row.product_ref, "product_name": names.get(row.product_ref),
                "total_quantity": row.total_quantity, "total_revenue": row.total_revenue,
            }
            for row in rows
        ], has_more

    async def get_sold(self, from_date: datetime.datetime, to_date: datetime.datetime, limit: int,
                        status: SoldStatus = SoldStatus.MOST,
                        cursor: tuple[decimal.Decimal, bytes] | None = None):
        return await self._get_sales(from_date=from_date, to_date=to_date, limit=limit,
                                      descending=status == SoldStatus.MOST, cursor=cursor)

    async def get_sales_summary(self, branch_id: bytes, limit: int,
                                 from_date: datetime.datetime | None = None, to_date: datetime.datetime | None = None,
                                 sort_by: ProductSortBy = ProductSortBy.REVENUE,
                                 cursor: tuple[decimal.Decimal, bytes] | None = None):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
                Order.branch_ref == branch_id)
            if from_date is not None and to_date is not None:
                query = query.where(Order.date_time >= from_date, Order.date_time < to_date)
            return query

        return await self._product_stats(apply_filters, limit, sort_by, cursor)

    async def get_client_stats(self, client_id: bytes, limit: int,
                                from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None,
                                sort_by: ProductSortBy = ProductSortBy.REVENUE,
                                 cursor: tuple[decimal.Decimal, bytes] | None = None):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
                Order.client_ref == client_id)
            if from_time is not None and to_time is not None:
                query = query.where(Order.date_time >= from_time, Order.date_time < to_time)
            return query

        return await self._product_stats(apply_filters, limit, sort_by, cursor)

    async def get_territory_stats(self, territory_id: bytes, limit: int,
                                   from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None,
                                   sort_by: ProductSortBy = ProductSortBy.REVENUE,
                                 cursor: tuple[decimal.Decimal, bytes] | None = None):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).join(
                Client, Client.id == Order.client_ref
            ).where(Client.territory_ref == territory_id)
            if from_time is not None and to_time is not None:
                query = query.where(Order.date_time >= from_time, Order.date_time < to_time)
            return query

        return await self._product_stats(apply_filters, limit, sort_by, cursor)

    async def _product_stats(self, apply_filters, limit: int, sort_by: ProductSortBy,
                              cursor: tuple[decimal.Decimal, bytes] | None = None):
        quantity_sold = func.sum(OrderLineItem.quantity).label("quantity_sold")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        profit = func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("profit")
        sort_expression = {
            ProductSortBy.QUANTITY_SOLD: func.sum(OrderLineItem.quantity),
            ProductSortBy.REVENUE: func.sum(OrderLineItem.sale_total),
            ProductSortBy.PROFIT: func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total),
        }[sort_by]
        sort_column = {
            ProductSortBy.QUANTITY_SOLD: quantity_sold,
            ProductSortBy.REVENUE: revenue,
            ProductSortBy.PROFIT: profit,
        }[sort_by]

        totals_query = apply_filters(select(
            func.sum(OrderLineItem.sale_total).label("total_revenue"),
            func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("total_profit"),
        ))
        await self.session.execute(text("SET LOCAL work_mem = '128MB'"))
        totals = (await self.session.execute(totals_query)).one()

        products_query = apply_filters(select(
            OrderLineItem.product_ref,
            quantity_sold,
            revenue,
            profit,
        )).group_by(OrderLineItem.product_ref)
        # Aggregate keyset lives in HAVING; product_ref is the tie-breaker.
        if cursor is not None:
            products_query = products_query.having(
                tuple_(sort_expression, OrderLineItem.product_ref) < tuple_(*cursor))
        products_query = products_query.order_by(
            sort_column.desc(), OrderLineItem.product_ref.desc()
        ).limit(limit + 1)
        rows = (await self.session.execute(products_query)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        names = await fetch_names(self.session, Product.id, Product.full_name,
                                   [row.product_ref for row in rows])
        products = [
            {
                "id": row.product_ref, "product_name": names.get(row.product_ref),
                "quantity_sold": row.quantity_sold, "revenue": row.revenue, "profit": row.profit,
            }
            for row in rows
        ]

        return totals.total_revenue or 0, totals.total_profit or 0, products, has_more

    async def _compare_periods(self, current_start: datetime.datetime, current_end: datetime.datetime,
                                previous_start: datetime.datetime, branch_id: bytes):
        is_current = Order.date_time >= current_start
        current_revenue = func.coalesce(
            func.sum(case((is_current, OrderLineItem.sale_total), else_=0)), 0).label("current_revenue")
        previous_revenue = func.coalesce(
            func.sum(case((~is_current, OrderLineItem.sale_total), else_=0)), 0).label("previous_revenue")
        current_profit = func.coalesce(
            func.sum(case((is_current, OrderLineItem.sale_total - OrderLineItem.cost_total), else_=0)), 0
        ).label("current_profit")
        previous_profit = func.coalesce(
            func.sum(case((~is_current, OrderLineItem.sale_total - OrderLineItem.cost_total), else_=0)), 0
        ).label("previous_profit")

        query = select(current_revenue, previous_revenue, current_profit, previous_profit).select_from(
            OrderLineItem
        ).join(Order, Order.id == OrderLineItem.order_ref).where(
            Order.date_time >= previous_start, Order.date_time < current_end,
            Order.branch_ref == branch_id,
        )
        # Aggregates a full period of line items before collapsing to one row;
        # default work_mem spills that sort to disk (see get_agent_ratings).
        await self.session.execute(text("SET LOCAL work_mem = '128MB'"))
        row = (await self.session.execute(query)).one()

        def growth(current, previous):
            if previous == 0:
                return None
            return round((current - previous) / previous * 100, 2)

        return {
            "current_revenue": row.current_revenue,
            "previous_revenue": row.previous_revenue,
            "revenue_growth_percent": growth(row.current_revenue, row.previous_revenue),
            "current_profit": row.current_profit,
            "previous_profit": row.previous_profit,
            "profit_growth_percent": growth(row.current_profit, row.previous_profit),
        }

    async def get_short_sales_growth(self, reference_date: datetime.datetime, branch_id: bytes):
        """Daily/weekly/monthly buckets - each scans at most ~2 months of orders
        (~1s total), so these refresh on a 6h cycle."""
        day_start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = day_start - datetime.timedelta(days=day_start.weekday())
        month_start = day_start.replace(day=1)

        def add_months(date: datetime.datetime, months: int) -> datetime.datetime:
            month_index = date.month - 1 + months
            year = date.year + month_index // 12
            month = month_index % 12 + 1
            return date.replace(year=year, month=month, day=1)

        return {
            "daily": await self._compare_periods(
                current_start=day_start, current_end=day_start + datetime.timedelta(days=1),
                previous_start=day_start - datetime.timedelta(days=1), branch_id=branch_id),
            "weekly": await self._compare_periods(
                current_start=week_start, current_end=week_start + datetime.timedelta(days=7),
                previous_start=week_start - datetime.timedelta(days=7), branch_id=branch_id),
            "monthly": await self._compare_periods(
                current_start=month_start, current_end=add_months(month_start, 1),
                previous_start=add_months(month_start, -1), branch_id=branch_id),
        }

    async def get_yearly_sales_growth(self, reference_date: datetime.datetime, branch_id: bytes):
        """Yearly bucket alone - spans two calendar years of line items and
        measured ~3.8s unscoped, which is why it refreshes on its own 24h cycle
        rather than riding the 6h one."""
        year_start = reference_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return await self._compare_periods(
            current_start=year_start, current_end=year_start.replace(year=year_start.year + 1),
            previous_start=year_start.replace(year=year_start.year - 1), branch_id=branch_id)

    async def get_sales_growth(self, reference_date: datetime.datetime, branch_id: bytes):
        return {
            **await self.get_short_sales_growth(reference_date, branch_id),
            "yearly": await self.get_yearly_sales_growth(reference_date, branch_id),
        }
