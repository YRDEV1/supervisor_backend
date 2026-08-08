from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.employee import Employee, ROLE_SUPERVISOR, ROLE_SALES_REP

class EmployeeRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_all_supervisors(self):
        query = select(Employee.id, Employee.code, Employee.full_name, Employee.phone, Employee.login,
                       Employee.password, Employee.parent_id).where(Employee.parent_id == ROLE_SUPERVISOR.bytes)
        execution = await self.session.execute(query)
        return execution.all()
    
    async def get_supervisor_info(self, supervisor_id: bytes):
        query = select(Employee.id, Employee.parent_id, Employee.full_name).where(Employee.id==supervisor_id, Employee.parent_id==ROLE_SUPERVISOR.bytes)
        execution = await self.session.execute(query)
        return execution.one_or_none()
    
    async def get_supervisor_agents(self, supervisor_id: bytes):
        query = select(Employee.id, Employee.parent_id, Employee.full_name).where(Employee.id==supervisor_id, Employee.parent_id==ROLE_SALES_REP.bytes)
        execution = await self.session.execute(query)
        return execution.all()
    
    async def get_all_agents(self, name: str | None = None):
        query = select(Employee.id, Employee.full_name, Employee.parent_id).where(Employee.parent_id==ROLE_SALES_REP.bytes)
        execution = await self.session.execute(query)
        rows = execution.all()
        if name:
            lowered = name.lower()
            rows = [row for row in rows if lowered in row.full_name.lower()]
        return rows
    
    async def get_agent_info(self, agent_id: bytes):
        query = select(Employee.id, Employee.full_name, Employee.parent_id, Employee.default_shift_start, Employee.default_shift_end).where(Employee.id==agent_id, Employee.parent_id==ROLE_SALES_REP.bytes)
        execution = await self.session.execute(query)
        return execution.one_or_none()

    async def get_by_credentials(self, login: str, password: str):
        query = select(Employee.id, Employee.parent_id, Employee.full_name).where(
            Employee.login == login, Employee.password == password, Employee.is_marked_for_deletion == False,
        )
        execution = await self.session.execute(query)
        return execution.one_or_none()