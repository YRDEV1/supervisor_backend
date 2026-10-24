from fastapi import APIRouter, Depends, HTTPException, Query

from agents.onec.repositories.employee import EmployeeRepository as OnecEmployeeRepository
from agents.onec.repositories.order import OrderRepository as OnecOrderRepository
from agents.src.repositories.agent import AgentRepository
from agents.src.schemas.supervisor import SupervisorAgentListResponse
from agents.src.services.supervisor_agent_service import get_supervisor_agents_with_stats
from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.schemas.supervisor import SupervisorDetailResponse, AgentDetailResponse
from supervisor.src.core.auth import require_supervisor, CurrentUser

employee_router = APIRouter(tags=["Supervisor details"], prefix="/employee", dependencies=[Depends(require_supervisor)])

@employee_router.get("/supervisors/info", summary="Supervisor details")
async def get_supervisor_details(current_user: CurrentUser = Depends(require_supervisor),
                                  employee_repo: EmployeeRepository = Depends()) -> SupervisorDetailResponse:
    supervisor = await employee_repo.get_supervisor_info(supervisor_id=current_user.id)
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor not found")

    return supervisor

@employee_router.get("/supervisors/agents", summary="Supervisor agents")
async def get_supervisor_agents(page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=200),
                                current_user: CurrentUser = Depends(require_supervisor),
                                agent_repo: AgentRepository = Depends(),
                                onec_employee_repo: OnecEmployeeRepository = Depends(),
                                onec_order_repo: OnecOrderRepository = Depends()) -> list[SupervisorAgentListResponse]:
    return await get_supervisor_agents_with_stats(current_user.id, (page - 1) * limit, limit,
                                                  agent_repo, onec_employee_repo, onec_order_repo)

@employee_router.get("/supervisors/agents/info", summary="Get agent details")
async def get_agent_info(agent_id: str, employee_repo: EmployeeRepository = Depends()) -> AgentDetailResponse:
    agent = await employee_repo.get_agent_info(agent_id=bytes.fromhex(agent_id))
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found")
    
    return agent