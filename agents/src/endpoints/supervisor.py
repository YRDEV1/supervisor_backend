from fastapi import APIRouter, Depends, Query

from agents.onec.repositories.employee import EmployeeRepository
from agents.onec.repositories.order import OrderRepository
from agents.src.core.exceptions import NotFoundException
from agents.src.core.response import CustomResponse
from agents.src.repositories.agent import AgentRepository
from agents.src.schemas.common import HexId
from agents.src.schemas.employee import EmployeeListResponse
from agents.src.schemas.supervisor import SupervisorAgentListResponse
from agents.src.services.supervisor_agent_service import get_supervisor_agents_with_stats
from supervisor.src.core.auth import require_supervisor

supervisor_router = APIRouter(
    tags=["Supervisors"], prefix="/supervisors", dependencies=[Depends(require_supervisor)]
)


@supervisor_router.get("", response_model=list[EmployeeListResponse])
async def get_all_supervisors_endpoint(employee_repo: EmployeeRepository = Depends()):
    rows = await employee_repo.get_all_supervisors()
    return CustomResponse([EmployeeListResponse.model_validate(row, from_attributes=True) for row in rows])


@supervisor_router.get("/{supervisor_id}/agents", response_model=list[SupervisorAgentListResponse])
async def get_all_supervisor_agents_endpoint(
    supervisor_id: HexId,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    agent_repo: AgentRepository = Depends(),
    employee_repo: EmployeeRepository = Depends(),
    order_repo: OrderRepository = Depends(),
):
    is_supervisor_exists = await employee_repo.get_supervisor_by_id(supervisor_id)
    if not is_supervisor_exists:
        raise NotFoundException("Supervisor not found")

    agents = await get_supervisor_agents_with_stats(
        supervisor_id, (page - 1) * limit, limit, agent_repo, employee_repo, order_repo
    )
    return CustomResponse(agents)
