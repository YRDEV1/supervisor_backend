from pydantic import BaseModel

from agents.src.schemas.common import HexId, Number


class EmployeeListResponse(BaseModel):
    id: HexId
    full_name: str
    code: Number | None
