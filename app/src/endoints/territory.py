import datetime

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.src.repositories.territory import TerritoryRepository
from app.src.schemas.territory import TerritoriesResponse, TerritorySortBy
from app.src.core.auth import require_supervisor
from app.src.core.types import NaiveDatetime

territory_router = APIRouter(tags=["Territory details"], prefix="/territory", dependencies=[Depends(require_supervisor)])

@territory_router.get("/all", summary="Get all territories")
async def get_all_territories(order_by: TerritorySortBy | None = None, from_time: NaiveDatetime | None = None,
                               to_time: NaiveDatetime | None = None, page: int = 1, limit: int = 25,
                               territory_repo: TerritoryRepository = Depends()) -> List[TerritoriesResponse]:
    if order_by is None and (from_time is not None or to_time is not None):
        raise HTTPException(status_code=400, detail="Select an order_by filter (revenue or profit) to use from_time/to_time")

    return await territory_repo.get_all(page=page, limit=limit, order_by=order_by, from_time=from_time, to_time=to_time)
