import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.src.repositories.order import OrderRepository
from app.src.schemas.order import (
    OrderResponse, OrderStatusResponse, OrderDetailResponse, OrderProductResponse, OrderSortDirection,
)
from app.src.models.order import get_order_status_label
from app.src.core.auth import require_supervisor
from app.src.core.types import NaiveDatetime

order_router = APIRouter(tags=["Order details"], prefix="/order", dependencies=[Depends(require_supervisor)])

@order_router.get("/all", summary="Get orders")
async def get_all_orders(from_date: NaiveDatetime, to_date: NaiveDatetime, supervisor_id: str,
                          status: str | None = None,
                          sort_direction: OrderSortDirection = OrderSortDirection.NEWEST_FIRST,
                          page: int = 1, limit: int = 25,
                          order_repo: OrderRepository = Depends()) -> List[OrderResponse]:
    rows = await order_repo.get_all(from_date=from_date, to_date=to_date, page=page, limit=limit, status=status,
                                     supervisor_id=bytes.fromhex(supervisor_id), sort_direction=sort_direction)
    return [
        OrderResponse(order_id=row.order_id, order_number=row.order_number, order_time=row.order_time,
                      client_code=row.client_code, client_name=row.client_name,
                      status=get_order_status_label(row.status_ref))
        for row in rows
    ]

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
