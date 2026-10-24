import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from agents.onec.repositories.employee import EmployeeRepository
from agents.onec.repositories.order import OrderRepository
from agents.src.core.exceptions import AlreadyExistsException, NotFoundException
from agents.src.core.response import CustomResponse
from agents.src.repositories.agent import AgentRepository
from agents.src.schemas.agent import (
    AgentCreationForm,
    AgentInfoResponse,
    AgentListResponse,
    AgentStatsResponse,
    AgentUpdateForm,
)
from agents.src.schemas.common import HexId
from agents.src.schemas.employee import EmployeeListResponse
from agents.src.utils.utils import to_naive_utc
from supervisor.src.core.auth import require_supervisor

agent_router = APIRouter(tags=["Agents"], prefix="/agents", dependencies=[Depends(require_supervisor)])

AGENT_NAME_MAX_LENGTH = 100


@agent_router.post("", response_model=AgentInfoResponse, status_code=201)
async def create_agent_endpoint(
    form: AgentCreationForm,
    agent_repo: AgentRepository = Depends(),
    employee_repo: EmployeeRepository = Depends(),
):
    if len(form.agent_name) > AGENT_NAME_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"Agent name must be at most {AGENT_NAME_MAX_LENGTH} characters")

    is_supervisor_exists = await employee_repo.get_supervisor_by_id(form.supervisor_id)
    if not is_supervisor_exists:
        raise NotFoundException("Supervisor not found")

    is_agent_exists = await agent_repo.get_agent_by_name(form.agent_name)
    if is_agent_exists:
        raise AlreadyExistsException("Agent name already exists")

    try:
        agent = await agent_repo.create_agent(form.model_dump())
    except IntegrityError:
        # Another request saved it first
        raise AlreadyExistsException("Agent name already exists")
    return CustomResponse(AgentInfoResponse.model_validate(agent), status_code=201)


@agent_router.get("", response_model=list[EmployeeListResponse])
async def get_all_agents_endpoint(employee_repo: EmployeeRepository = Depends()):
    rows = await employee_repo.get_all_agents()
    return CustomResponse([EmployeeListResponse.model_validate(row, from_attributes=True) for row in rows])


@agent_router.get("/saved", response_model=list[AgentListResponse])
async def get_all_saved_agents_endpoint(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=200, ge=1, le=200),
    agent_repo: AgentRepository = Depends(),
    employee_repo: EmployeeRepository = Depends(),
):
    agents = await agent_repo.get_all((page - 1) * limit, limit)
    supervisor_names = await employee_repo.get_names_by_ids(list({agent.supervisor_id for agent in agents}))
    return CustomResponse(
        [
            AgentListResponse(
                id=agent.id,
                supervisor_id=agent.supervisor_id,
                supervisor_name=supervisor_names.get(agent.supervisor_id),
                agent_name=agent.agent_name,
                created_at=agent.created_at,
            )
            for agent in agents
        ]
    )


@agent_router.get("/{agent_id}", response_model=AgentStatsResponse)
async def get_agent_info_endpoint(
    agent_id: HexId,
    top_products_limit: int = Query(default=5, ge=1, le=50),
    from_time: datetime.datetime | None = Query(default=None),
    to_time: datetime.datetime | None = Query(default=None),
    employee_repo: EmployeeRepository = Depends(),
    order_repo: OrderRepository = Depends(),
):
    if from_time:
        from_time = to_naive_utc(from_time)
    if to_time:
        to_time = to_naive_utc(to_time)
    if from_time and to_time and from_time >= to_time:
        raise HTTPException(status_code=422, detail="from_time must be earlier than to_time")

    is_agent_exists = await employee_repo.get_agent_by_id(agent_id)
    if not is_agent_exists:
        raise NotFoundException("Agent not found")

    stats = await order_repo.get_agent_stats(agent_id, top_products_limit, from_time, to_time)
    return CustomResponse(
        AgentStatsResponse(
            id=is_agent_exists.id,
            full_name=is_agent_exists.full_name,
            code=is_agent_exists.code,
            order_count=stats.order_count,
            total_revenue=stats.total_revenue,
            first_order=stats.first_order,
            last_order=stats.last_order,
            distinct_clients=stats.distinct_clients,
            top_products=stats.top_products or [],
        )
    )


@agent_router.patch("/{agent_id}", response_model=AgentInfoResponse)
async def update_agent_endpoint(
    agent_id: int,
    form: AgentUpdateForm,
    agent_repo: AgentRepository = Depends(),
    employee_repo: EmployeeRepository = Depends(),
):
    is_agent_exists = await agent_repo.get_agent_by_id(agent_id)
    if not is_agent_exists:
        raise NotFoundException("Agent not found")

    payload = {}
    if form.agent_name and form.agent_name != is_agent_exists.agent_name:
        if len(form.agent_name) > AGENT_NAME_MAX_LENGTH:
            raise HTTPException(
                status_code=422, detail=f"Agent name must be at most {AGENT_NAME_MAX_LENGTH} characters"
            )
        is_name_taken = await agent_repo.get_agent_by_name(form.agent_name)
        if is_name_taken:
            raise AlreadyExistsException("Agent name already exists")
        payload["agent_name"] = form.agent_name
    if form.supervisor_id and form.supervisor_id != is_agent_exists.supervisor_id:
        is_supervisor_exists = await employee_repo.get_supervisor_by_id(form.supervisor_id)
        if not is_supervisor_exists:
            raise NotFoundException("Supervisor not found")
        payload["supervisor_id"] = form.supervisor_id

    agent = is_agent_exists
    if payload:
        try:
            agent = await agent_repo.update_agent(agent_id, payload)
        except IntegrityError:
            raise AlreadyExistsException("Agent name already exists")
    return CustomResponse(AgentInfoResponse.model_validate(agent))


@agent_router.delete("/{agent_id}", status_code=204)
async def delete_agent_endpoint(agent_id: int, agent_repo: AgentRepository = Depends()):
    is_agent_exists = await agent_repo.get_agent_by_id(agent_id)
    if not is_agent_exists:
        raise NotFoundException("Agent not found")

    await agent_repo.delete_agent(agent_id)
    return CustomResponse(status_code=204)
