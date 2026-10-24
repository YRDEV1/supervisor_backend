import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.repositories.sales_trend import SalesTrendRepository
from supervisor.src.repositories.visit import VisitRepository
from supervisor.src.repositories.order import OrderRepository
from supervisor.src.schemas.order import (
    OrderResponse, OrderStatusResponse, OrderDetailResponse, OrderProductResponse, OrderSortDirection,
    OrderPageResponse
)
from supervisor.src.models.order import get_order_status_label
from supervisor.src.core.auth import require_supervisor, CurrentUser
from supervisor.src.core.cursor import decode_datetime_id_cursor, encode_cursor
from supervisor.src.core.types import NaiveDatetime, TASHKENT_TZ

order_router = APIRouter(tags=["Order details"], prefix="/order", dependencies=[Depends(require_supervisor)])

@order_router.get("/all", summary="Get orders (keyset paginated)")
async def get_all_orders(
    from_date: datetime.date | None = None,
    to_date: datetime.date | None = None,
    status: str | None = None,
    sort_direction: OrderSortDirection = OrderSortDirection.NEWEST_FIRST,
    cursor: str | None = None,
    limit: int = 25,
    current_user: CurrentUser = Depends(require_supervisor),
    employee_repo: EmployeeRepository = Depends(),
    sales_trend_repo: SalesTrendRepository = Depends(),
    visit_repo: VisitRepository = Depends(),
    order_repo: OrderRepository = Depends()
) -> OrderPageResponse:
    supervisor_agents_ids = await employee_repo.get_supervisor_agent_ids(current_user.id)

    # Dynamic date range resolution
    now_tashkent = datetime.datetime.now(TASHKENT_TZ)
    
    start_dt = (
        datetime.datetime.combine(from_date, datetime.time.min)
        if from_date
        else datetime.datetime.combine(now_tashkent.date(), datetime.time.min)
    )

    end_dt = (
        datetime.datetime.combine(to_date, datetime.time.max)
        if to_date
        else start_dt + datetime.timedelta(days=1)
    )
    
    required_target = await sales_trend_repo.get_month_required_target(
        agent_ids=supervisor_agents_ids,
        reference_date=start_dt.date(),
        branch_id=current_user.branch_id,
    )

    visited_clients, not_visited_clients = await visit_repo.get_client_visit_stats(
        agent_ids=supervisor_agents_ids,
        from_date=start_dt,
        to_date=end_dt
    )

    rows, has_more, total_revenue, total_orders_count = await order_repo.get_all(
        from_date=start_dt,
        to_date=end_dt,
        limit=limit,
        status=status,
        cursor=decode_datetime_id_cursor(cursor) if cursor else None,
        agent_ids=supervisor_agents_ids,
        sort_direction=sort_direction
    )

    return OrderPageResponse(
        items=[
            OrderResponse(
                order_id=row.order_id,
                order_number=row.order_number,
                order_time=row.order_time,
                client_code=row.client_code,
                client_name=row.client_name,
                status=get_order_status_label(row.status_ref),
            )
            for row in rows
        ],
        visited_clients=visited_clients,
        not_visited_clients=not_visited_clients,
        current_revenue=float(total_revenue),
        total_order_count=total_orders_count,  # Top-level property
        target=required_target,
        next_cursor=encode_cursor(rows[-1].order_time, rows[-1].order_id) if has_more and rows else None,
    )

@order_router.get("/statuses", summary="Get order statuses")
async def get_order_statuses(order_repo: OrderRepository = Depends()) -> List[OrderStatusResponse]:
    rows = await order_repo.get_status_counts()
    counts: dict[str, int] = {}
    for row in rows:
        label = get_order_status_label(row.status_ref)
        counts[label] = counts.get(label, 0) + row.count
    return [OrderStatusResponse(status=label, count=count) for label, count in counts.items()]

@order_router.get("/info", summary="Get order details")
async def get_order_info(order_id: str, order_repo: OrderRepository = Depends()) -> OrderDetailResponse:
    row = await order_repo.get_by_id(order_id=bytes.fromhex(order_id))
    if not row:
        raise HTTPException(status_code=400, detail="Order not found")

    product_rows = await order_repo.get_products(order_id=bytes.fromhex(order_id))

    return OrderDetailResponse(
        order_id=row.order_id, order_number=row.order_number, order_time=row.order_time,
        is_posted=row.is_posted, status=get_order_status_label(row.status_ref),
        client_id=row.client_id, client_code=row.client_code, client_name=row.client_name,
        client_phone=row.client_phone, branch_name=row.branch_name,
        agent_code=row.agent_code, agent_name=row.agent_name, total=row.total,
        products=[OrderProductResponse.model_validate(product_row) for product_row in product_rows],
    )
