from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.src.repositories.employee import EmployeeRepository
from app.src.schemas.supervisor import SupervisorsResponse, SupervisorDetailResponse, SupervisorAgentsResponse, AgentDetailResponse
from app.src.core.auth import require_supervisor

employee_router = APIRouter(tags=["Supervisor details"], prefix="/employee", dependencies=[Depends(require_supervisor)])

@employee_router.get("/supervisors", summary="Get all supervisors")
async def get_all_supervisors(employee_repo: EmployeeRepository = Depends()) -> List[SupervisorsResponse]:
    return await employee_repo.get_all_supervisors()

@employee_router.get("/supervisors/info", summary="Supervisor details")
async def get_supervisor_details(supervisor_id: str, employee_repo: EmployeeRepository = Depends()) -> SupervisorDetailResponse:
    supervisor =  await employee_repo.get_supervisor_info(supervisor_id=bytes.fromhex(supervisor_id))
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor not found")
    
    return supervisor

@employee_router.get("/supervisors/agents", summary="Supervisor agents")
async def get_supervisor_agents(supervisor_id: str, employee_repo: EmployeeRepository = Depends()) -> List[SupervisorAgentsResponse]:
    return await employee_repo.get_supervisor_agents(supervisor_id=bytes.fromhex(supervisor_id))

@employee_router.get("/agents", summary="Get all agents")
async def get_all_agents(name: str | None = None, employee_repo: EmployeeRepository = Depends()) -> List[SupervisorAgentsResponse]:
    return await employee_repo.get_all_agents(name=name)

@employee_router.get("/supervisors/agents/info", summary="Get agent details")
async def get_agent_info(agent_id: str, employee_repo: EmployeeRepository = Depends()) -> AgentDetailResponse:
    agent = await employee_repo.get_agent_info(agent_id=bytes.fromhex(agent_id))
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found")
    
    return agent