import datetime

from pydantic import BaseModel

from agents.src.schemas.common import HexId, Number


class SupervisorAgentListResponse(BaseModel):
    agent_id: int
    supervisor_id: HexId
    agent_name: str
    created_at: datetime.datetime
    order_count: int
    total_revenue: Number
    profit: Number
