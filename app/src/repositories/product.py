import datetime

from sqlalchemy import case, exists, func
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from app.src.core.database import ASYNC_SESSION
from app.src.models.product import Product, ROOT_PARENT_ID
from app.src.models.order import Order
from app.src.models.order_line_item import OrderLineItem
from app.src.models.client import Client
from app.src.schemas.product import ProductSortBy

class ProductRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_categories(self, page: int, limit: int, name: str | None = None):
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
        ).order_by(Product.id)
        execution = await self.session.execute(query)
        rows = execution.all()

        if name:
            lowered = name.lower()
            rows = [row for row in rows if lowered in row.category_name.lower()]

        start = (page - 1) * limit
        return rows[start:start + limit]

    async def get_all(self, page: int, limit: int, category_id: bytes | None = None):
        query = select(
            Product.id,
            Product.full_name.label("product_name"),
        )
        if category_id is not None:
            query = query.where(Product.parent_id == category_id)
        query = query.order_by(Product.id).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def _get_sales(self, from_date: datetime.datetime, to_date: datetime.datetime, page: int, limit: int,
                          descending: bool):
        total_quantity = func.sum(OrderLineItem.quantity).label("total_quantity")
        total_revenue = func.sum(OrderLineItem.sale_total).label("total_revenue")
        query = select(
            Product.id,
            Product.full_name.label("product_name"),
            total_quantity,
            total_revenue,
        ).select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).join(
            Product, Product.id == OrderLineItem.product_ref
        ).where(
            Order.date_time >= from_date, Order.date_time < to_date
        ).group_by(Product.id, Product.full_name)
        query = query.order_by(total_quantity.desc() if descending else total_quantity.asc())
        query = query.limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_most_sold(self, from_date: datetime.datetime, to_date: datetime.datetime, page: int, limit: int):
        return await self._get_sales(from_date=from_date, to_date=to_date, page=page, limit=limit, descending=True)

    async def get_least_sold(self, from_date: datetime.datetime, to_date: datetime.datetime, page: int, limit: int):
        return await self._get_sales(from_date=from_date, to_date=to_date, page=page, limit=limit, descending=False)

    async def get_sales_summary(self, branch_id: bytes, page: int, limit: int,
                                 from_date: datetime.datetime | None = None, to_date: datetime.datetime | None = None,
                                 sort_by: ProductSortBy = ProductSortBy.REVENUE):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
                Order.branch_ref == branch_id)
            if from_date is not None and to_date is not None:
                query = query.where(Order.date_time >= from_date, Order.date_time < to_date)
            return query

        return await self._product_stats(apply_filters, page, limit, sort_by)

    async def get_client_stats(self, client_id: bytes, page: int, limit: int,
                                from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None,
                                sort_by: ProductSortBy = ProductSortBy.REVENUE):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).where(
                Order.client_ref == client_id)
            if from_time is not None and to_time is not None:
                query = query.where(Order.date_time >= from_time, Order.date_time < to_time)
            return query

        return await self._product_stats(apply_filters, page, limit, sort_by)

    async def get_territory_stats(self, territory_id: bytes, page: int, limit: int,
                                   from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None,
                                   sort_by: ProductSortBy = ProductSortBy.REVENUE):
        def apply_filters(query):
            query = query.select_from(OrderLineItem).join(Order, Order.id == OrderLineItem.order_ref).join(
                Client, Client.id == Order.client_ref
            ).where(Client.territory_ref == territory_id)
            if from_time is not None and to_time is not None:
                query = query.where(Order.date_time >= from_time, Order.date_time < to_time)
            return query

        return await self._product_stats(apply_filters, page, limit, sort_by)

    async def _product_stats(self, apply_filters, page: int, limit: int, sort_by: ProductSortBy):
        quantity_sold = func.sum(OrderLineItem.quantity).label("quantity_sold")
        revenue = func.sum(OrderLineItem.sale_total).label("revenue")
        profit = func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("profit")
        sort_column = {
            ProductSortBy.QUANTITY_SOLD: quantity_sold,
            ProductSortBy.REVENUE: revenue,
            ProductSortBy.PROFIT: profit,
        }[sort_by]

        totals_query = apply_filters(select(
            func.sum(OrderLineItem.sale_total).label("total_revenue"),
            func.sum(OrderLineItem.sale_total - OrderLineItem.cost_total).label("total_profit"),
        ))
        totals = (await self.session.execute(totals_query)).one()

        products_query = apply_filters(select(
            Product.id,
            Product.full_name.label("product_name"),
            quantity_sold,
            revenue,
            profit,
        )).join(Product, Product.id == OrderLineItem.product_ref).group_by(
            Product.id, Product.full_name
        ).order_by(sort_column.desc()).limit(limit).offset((page - 1) * limit)
        products = (await self.session.execute(products_query)).all()

        return totals.total_revenue or 0, totals.total_profit or 0, products

    async def _compare_periods(self, current_start: datetime.datetime, current_end: datetime.datetime,
                                previous_start: datetime.datetime):
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
            Order.date_time >= previous_start, Order.date_time < current_end
        )
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

    async def get_sales_growth(self, reference_date: datetime.datetime):
        day_start = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = day_start - datetime.timedelta(days=day_start.weekday())
        month_start = day_start.replace(day=1)
        year_start = day_start.replace(month=1, day=1)

        def add_months(date: datetime.datetime, months: int) -> datetime.datetime:
            month_index = date.month - 1 + months
            year = date.year + month_index // 12
            month = month_index % 12 + 1
            return date.replace(year=year, month=month, day=1)

        return {
            "daily": await self._compare_periods(
                current_start=day_start, current_end=day_start + datetime.timedelta(days=1),
                previous_start=day_start - datetime.timedelta(days=1)),
            "weekly": await self._compare_periods(
                current_start=week_start, current_end=week_start + datetime.timedelta(days=7),
                previous_start=week_start - datetime.timedelta(days=7)),
            "monthly": await self._compare_periods(
                current_start=month_start, current_end=add_months(month_start, 1),
                previous_start=add_months(month_start, -1)),
            "yearly": await self._compare_periods(
                current_start=year_start, current_end=year_start.replace(year=year_start.year + 1),
                previous_start=year_start.replace(year=year_start.year - 1)),
        }
