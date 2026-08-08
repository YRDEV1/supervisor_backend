import datetime

from sqlalchemy import func, exists
from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.visit import Visit, VISIT_OUTCOME_CHECK_IN, VISIT_OUTCOME_CHECK_OUT
from app.src.models.client import Client
from app.src.models.territory import Territory
from app.src.models.employee import Employee

class VisitRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_agent_visit_history(self, agent_id: bytes, from_date: datetime.datetime, to_date: datetime.datetime,
                                       page: int, limit: int, client_id: bytes | None = None):
        query = select(
            Client.id.label("client_id"),
            Client.code.label("client_code"),
            Client.full_name.label("client_name"),
            func.min(Visit.period).filter(Visit.outcome_ref == VISIT_OUTCOME_CHECK_IN.bytes).label("check_in"),
            func.max(Visit.period).filter(Visit.outcome_ref == VISIT_OUTCOME_CHECK_OUT.bytes).label("check_out"),
            func.max(Visit.period).label("request_time"),
        ).select_from(Visit).join(Client, Client.id == Visit.outlet_ref).where(
            Visit.agent_ref == agent_id, Visit.period >= from_date, Visit.period < to_date
        )
        if client_id is not None:
            query = query.where(Visit.outlet_ref == client_id)
        query = query.group_by(Client.id, Client.code, Client.full_name).order_by(func.min(Visit.period))
        query = query.limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_entry_count(self, agent_id: bytes, client_id: bytes, from_time: datetime.datetime, to_time: datetime.datetime):
        query = select(
            func.sum(1).label("entry_count"),
        ).where(
            Visit.agent_ref == agent_id, Visit.outlet_ref == client_id,
            Visit.period >= from_time, Visit.period < to_time,
        )
        execution = await self.session.execute(query)
        return execution.scalar_one()

    async def get_not_visited_clients(self, agent_id: bytes, since: datetime.datetime, page: int, limit: int):
        visited_before = exists(
            select(1).where(Visit.agent_ref == agent_id, Visit.outlet_ref == Client.id, Visit.period >= since)
        )
        ever_visited = exists(
            select(1).where(Visit.agent_ref == agent_id, Visit.outlet_ref == Client.id)
        )
        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
        ).where(ever_visited, ~visited_before).order_by(Client.code).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_agent_idle_periods(self, agent_id: bytes, from_date: datetime.datetime, to_date: datetime.datetime,
                                      threshold_minutes: int = 10):
        events = select(
            Visit.period,
            func.lag(Visit.period).over(order_by=Visit.period).label("prev_period"),
        ).where(
            Visit.agent_ref == agent_id, Visit.period >= from_date, Visit.period < to_date
        ).subquery()

        gap = events.c.period - events.c.prev_period
        query = select(
            events.c.prev_period.label("idle_start"),
            events.c.period.label("idle_end"),
        ).where(gap > datetime.timedelta(minutes=threshold_minutes)).order_by(events.c.prev_period)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_clients_not_visited_on_date(self, date: datetime.date, supervisor_id: bytes, page: int, limit: int):
        day_start = datetime.datetime.combine(date, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        supervisor_branch = select(Employee.branch_ref).where(Employee.id == supervisor_id).scalar_subquery()

        # Agents recorded under this supervisor in the visit register, restricted
        # to agents that also share the supervisor's own branch - `_fld1116rref`
        # (branch_ref) is shared by every employee at a branch, not unique to one
        # supervisor, so this narrows a same-branch-collision from matching too much.
        agent_ids = select(Visit.agent_ref).select_from(Visit).join(
            Employee, Employee.id == Visit.agent_ref
        ).where(
            Visit.supervisor_individual_ref == supervisor_branch,
            Employee.branch_ref == supervisor_branch,
        ).distinct()

        # Only the territories these agents actually cover (derived from their
        # own visit history), so clients outside that coverage never show up.
        agent_territories = select(Client.territory_ref).select_from(Visit).join(
            Client, Client.id == Visit.outlet_ref
        ).where(Visit.agent_ref.in_(agent_ids)).distinct()

        ever_visited = exists(
            select(1).where(Visit.agent_ref.in_(agent_ids), Visit.outlet_ref == Client.id)
        )
        visited_on_date = exists(
            select(1).where(
                Visit.agent_ref.in_(agent_ids), Visit.outlet_ref == Client.id,
                Visit.period >= day_start, Visit.period < day_end,
            )
        )

        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
        ).join(Territory, Territory.id == Client.territory_ref).where(
            Client.is_marked_for_deletion == False, Territory.territory_name != "Тугатилганлар",
            Client.territory_ref.in_(agent_territories),
            ever_visited, ~visited_on_date,
        ).order_by(Client.code).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()
