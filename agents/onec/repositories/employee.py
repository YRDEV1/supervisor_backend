from sqlalchemy import String, cast, or_, select

from agents.onec.database import ONEC_DB_SESSION
from agents.onec.models.employee import ROLE_SUPERVISOR, Employee
from agents.onec.models.order import Order
from agents.onec.models.visit import Visit


class EmployeeRepository:
    def __init__(self, db: ONEC_DB_SESSION):
        self.db = db

    async def get_supervisor_by_id(self, supervisor_id: bytes):
        query = select(Employee.id, Employee.full_name).where(
            Employee.id == supervisor_id,
            Employee.parent_id == ROLE_SUPERVISOR.bytes,
        )
        execution = await self.db.execute(query)
        return execution.one_or_none()

    async def get_all_supervisors(self):
        query = select(Employee.id, Employee.full_name, Employee.code).where(
            Employee.parent_id == ROLE_SUPERVISOR.bytes,
            Employee.is_marked_for_deletion.is_(False),
        )
        execution = await self.db.execute(query)
        return execution.all()

    async def get_agent_by_id(self, agent_id: bytes):
        query = select(Employee.id, Employee.full_name, Employee.code).where(Employee.id == agent_id)
        execution = await self.db.execute(query)
        return execution.one_or_none()

    async def get_all_agents(self):
        # Agent = appears in orders or visits
        agent_refs = select(Order.agent_ref).union_all(select(Visit.agent_ref))
        query = (
            select(Employee.id, Employee.full_name, Employee.code)
            .where(
                Employee.is_marked_for_deletion.is_(False),
                Employee.id.in_(agent_refs),
            )
            .order_by(Employee.full_name)
        )
        execution = await self.db.execute(query)
        return execution.all()

    async def get_names_by_ids(self, employee_ids: list[bytes]) -> dict[bytes, str]:
        if not employee_ids:
            return {}
        query = select(Employee.id, Employee.full_name).where(Employee.id.in_(employee_ids))
        execution = await self.db.execute(query)
        return {row.id: row.full_name for row in execution.all()}

    async def get_all_by_names(self, full_names: list[str]):
        if not full_names:
            return []
        # mvarchar needs a text cast
        full_name_text = cast(Employee.full_name, String)
        query = select(Employee.id, full_name_text.label("full_name")).where(full_name_text.in_(full_names))
        execution = await self.db.execute(query)
        return execution.all()
