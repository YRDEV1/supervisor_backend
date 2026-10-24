from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.employee import Employee, ROLE_SUPERVISOR, ROLE_SALES_REP
from supervisor.src.models.visit import Visit
from supervisor.src.models.territory import SupervisorTerritoryAssignment, SupervisorActiveTerritoryAssignment

class EmployeeRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_supervisor_info(self, supervisor_id: bytes):
        query = select(Employee.id, Employee.parent_id, Employee.full_name).where(Employee.id==supervisor_id, Employee.parent_id==ROLE_SUPERVISOR.bytes)
        execution = await self.session.execute(query)
        return execution.first()

    async def get_supervisor_agent_ids(self, supervisor_id: bytes) -> list[bytes]:
        """Every `ТП` agent linked to this supervisor, by either of two
        signals - the union, not just one:

        1. Territory overlap (via the direct assignment table, see
           DATA/SUPERVISOR_TERRITORY.md) - a candidate pool, not a verified
           current-team list. Picking a single "current" agent per territory
           was attempted via most-recent-order recency and empirically failed
           (0/7 against the documented ground truth for "Фазлиддин СВ", and a
           separate case where two different territories' "most recent"
           order both belonged to the same one agent) - no rule for this has
           been found in the data, so every candidate is returned instead of
           a guess. See DATA/SUPERVISOR_TERRITORY.md's "still unresolved" note.

        2. Visit register branch match - `Visit.supervisor_individual_ref`
           resolves to this supervisor's *branch*, not their individual
           employee id, despite the column name (confirmed: it never matches
           an Employee.id, only Employee.branch_ref). Added after a concrete
           case: 8 agents with thousands of recorded visits each under one
           supervisor's branch had zero territory-assignment rows pointing
           to her at all - the territory table was simply never filled in
           for them, and they were silently absent from her team.

        Known tradeoff of adding (2): several supervisors can share one
        branch (confirmed for this exact case), so an agent resolved only
        via branch match may now appear under more than one of them. Chosen
        deliberately - a supervisor silently missing real subordinates with
        heavy visit history is worse than an occasional duplicate listing
        across supervisors who share a branch.
        """
        sup_vt = aliased(SupervisorTerritoryAssignment)
        agent_vt = aliased(SupervisorTerritoryAssignment)
        by_territory = select(agent_vt.employee_ref).select_from(sup_vt).join(
            agent_vt, agent_vt.territory_ref == sup_vt.territory_ref
        ).join(
            Employee, Employee.id == agent_vt.employee_ref
        ).where(
            sup_vt.employee_ref == supervisor_id,
            Employee.parent_id == ROLE_SALES_REP.bytes,
            Employee.is_marked_for_deletion == False,
        )

        supervisor_branch = select(Employee.branch_ref).where(Employee.id == supervisor_id).limit(1).scalar_subquery()
        by_visit_branch = select(Visit.agent_ref).select_from(Visit).join(
            Employee, Employee.id == Visit.agent_ref
        ).where(
            Visit.supervisor_individual_ref == supervisor_branch,
            Employee.parent_id == ROLE_SALES_REP.bytes,
            Employee.is_marked_for_deletion == False,
        )

        query = by_territory.union(by_visit_branch)
        rows = (await self.session.execute(query)).scalars().all()
        return [ref for ref in rows if ref and ref != b"\x00" * 16]

    async def get_supervisor_branch_refs(self) -> list[bytes]:
        """Distinct branches covered by at least one supervisor - the cache is
        keyed per branch, not per supervisor, because supervisors sharing a
        branch see identical numbers and would otherwise recompute the same
        aggregate several times per cycle."""
        query = select(Employee.branch_ref).where(
            Employee.parent_id == ROLE_SUPERVISOR.bytes,
            Employee.is_marked_for_deletion == False,
        ).distinct()
        rows = (await self.session.execute(query)).scalars().all()
        return [ref for ref in rows if ref and ref != b"\x00" * 16]

    async def get_shift(self, employee_id: bytes):
        """Shift-time template for any employee row (agent or supervisor) -
        used by sales-trend to bound the daily granularity's hourly buckets
        to the team's actual working hours instead of a hardcoded window."""
        query = select(Employee.default_shift_start, Employee.default_shift_end).where(
            Employee.id == employee_id).limit(1)
        return (await self.session.execute(query)).first()

    async def get_branch_ref(self, employee_id: bytes) -> bytes | None:
        query = select(Employee.branch_ref).where(Employee.id == employee_id).limit(1)
        branch_ref = (await self.session.execute(query)).scalar()
        if not branch_ref or branch_ref == b"\x00" * 16:
            return None
        return branch_ref

    async def get_supervisor_territory_ids(self, supervisor_id: bytes) -> list[bytes]:
        """The employee's current/active territories, via `_vt4708` - the
        best available approximation of the true current list (excludes
        deactivated "excess" territories that the fuller `_vt4705` table
        wrongly includes), though not fully authoritative for every
        employee (see DATA/SUPERVISOR_TERRITORY.md's two documented
        limitations). Not the branch/visit-pooled proxy used elsewhere,
        which mixes together every supervisor sharing a branch since the
        visit register only carries branch-level identity."""
        query = select(SupervisorActiveTerritoryAssignment.territory_ref).where(
            SupervisorActiveTerritoryAssignment.employee_ref == supervisor_id
        ).order_by(SupervisorActiveTerritoryAssignment.line_no)
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows)

    async def get_agent_info(self, agent_id: bytes):
        query = select(Employee.id, Employee.full_name, Employee.parent_id, Employee.default_shift_start, Employee.default_shift_end).where(Employee.id==agent_id, Employee.parent_id==ROLE_SALES_REP.bytes)
        execution = await self.session.execute(query)
        return execution.first()

    async def get_by_credentials(self, login: str, password: str):
        # login/password are typed MVARCHAR (see models/core.py) so the bind
        # params aren't cast to ::VARCHAR - this DB export has no
        # `mvarchar = varchar` operator.
        query = select(Employee.id, Employee.parent_id, Employee.full_name).where(
            Employee.login == login, Employee.password == password,
            Employee.is_marked_for_deletion == False,
        )
        execution = await self.session.execute(query)
        return execution.first()