from agents.onec.repositories.employee import EmployeeRepository
from agents.onec.repositories.order import OrderRepository
from agents.src.repositories.agent import AgentRepository
from agents.src.schemas.supervisor import SupervisorAgentListResponse


async def get_supervisor_agents_with_stats(
    supervisor_id: bytes,
    offset: int,
    limit: int,
    agent_repo: AgentRepository,
    employee_repo: EmployeeRepository,
    order_repo: OrderRepository,
) -> list[SupervisorAgentListResponse]:
    agents = await agent_repo.get_all_by_supervisor_id(supervisor_id, offset, limit)

    # Saved agents only know names
    employees = await employee_repo.get_all_by_names([agent.agent_name for agent in agents])
    name_by_employee_id = {employee.id: employee.full_name for employee in employees}

    # Same name means summed stats
    stats_by_name = {}
    for row in await order_repo.get_agents_stats(list(name_by_employee_id)):
        stats = stats_by_name.setdefault(
            name_by_employee_id[row.agent_ref], {"order_count": 0, "total_revenue": 0, "profit": 0}
        )
        stats["order_count"] += row.order_count
        stats["total_revenue"] += row.total_revenue
        stats["profit"] += row.profit

    empty_stats = {"order_count": 0, "total_revenue": 0, "profit": 0}
    return [
        SupervisorAgentListResponse(
            agent_id=agent.id,
            supervisor_id=agent.supervisor_id,
            agent_name=agent.agent_name,
            created_at=agent.created_at,
            **stats_by_name.get(agent.agent_name, empty_stats),
        )
        for agent in agents
    ]
