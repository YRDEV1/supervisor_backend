import datetime
import decimal

from sqlalchemy import func, exists, tuple_
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.visit import Visit, VISIT_OUTCOME_CHECK_IN, VISIT_OUTCOME_CHECK_OUT
from supervisor.src.models.client import Client
from supervisor.src.models.territory import Territory, EXCLUDED_TERRITORY_NAMES
from supervisor.src.repositories.utils import fetch_names

class VisitRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_agent_visit_history(self, agent_id: bytes, from_date: datetime.datetime, to_date: datetime.datetime,
                                       limit: int, client_id: bytes | None = None,
                                       cursor: tuple[datetime.datetime, bytes] | None = None):
        first_seen = func.min(Visit.period)
        query = select(
            Client.id.label("client_id"),
            Client.code.label("client_code"),
            func.min(Visit.period).filter(Visit.outcome_ref == VISIT_OUTCOME_CHECK_IN.bytes).label("check_in"),
            func.max(Visit.period).filter(Visit.outcome_ref == VISIT_OUTCOME_CHECK_OUT.bytes).label("check_out"),
            func.max(Visit.period).label("request_time"),
            first_seen.label("first_seen"),
        ).select_from(Visit).join(Client, Client.id == Visit.outlet_ref).where(
            Visit.agent_ref == agent_id, Visit.period >= from_date, Visit.period < to_date
        )
        if client_id is not None:
            query = query.where(Visit.outlet_ref == client_id)
        query = query.group_by(Client.id, Client.code)
        # Ordered by each client's first visit; the aggregate keyset goes in
        # HAVING, with client_id breaking ties on identical timestamps.
        if cursor is not None:
            query = query.having(tuple_(first_seen, Client.id) > tuple_(*cursor))
        query = query.order_by(first_seen.asc(), Client.id.asc()).limit(limit + 1)
        rows = (await self.session.execute(query)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        names = await fetch_names(self.session, Client.id, Client.full_name,
                                   [row.client_id for row in rows])
        return [
            {
                "client_id": row.client_id, "client_code": row.client_code,
                "client_name": names.get(row.client_id),
                "check_in": row.check_in, "check_out": row.check_out, "request_time": row.request_time,
                "first_seen": row.first_seen,
            }
            for row in rows
        ], has_more

    async def get_entry_count(self, agent_id: bytes, client_id: bytes, from_time: datetime.datetime, to_time: datetime.datetime):
        query = select(
            func.sum(1).label("entry_count"),
        ).where(
            Visit.agent_ref == agent_id, Visit.outlet_ref == client_id,
            Visit.period >= from_time, Visit.period < to_time,
        )
        execution = await self.session.execute(query)
        return execution.scalar_one()

    async def get_not_visited_clients(self, agent_id: bytes, since: datetime.datetime, limit: int,
                                       cursor: tuple[decimal.Decimal, bytes] | None = None):
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
        ).where(ever_visited, ~visited_before)
        if cursor is not None:
            query = query.where(tuple_(Client.code, Client.id) > tuple_(*cursor))
        query = query.order_by(Client.code, Client.id).limit(limit + 1)
        rows = (await self.session.execute(query)).all()
        return rows[:limit], len(rows) > limit

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

    async def get_clients_not_visited_on_date(self, date: datetime.date, agent_ids: list[bytes], limit: int,
                                               cursor: tuple[decimal.Decimal, bytes] | None = None):
        day_start = datetime.datetime.combine(date, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        if not agent_ids:
            return [], False

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
            Client.is_marked_for_deletion == False,
            Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES),
            Client.territory_ref.in_(agent_territories),
            ever_visited, ~visited_on_date,
        )
        if cursor is not None:
            query = query.where(tuple_(Client.code, Client.id) > tuple_(*cursor))
        query = query.order_by(Client.code, Client.id).limit(limit + 1)
        rows = (await self.session.execute(query)).all()
        return rows[:limit], len(rows) > limit

    async def get_client_visit_stats(
        self,
        agent_ids: list[bytes],
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> tuple[int, int]:
        if not agent_ids:
            return 0, 0

        start_dt = datetime.datetime.combine(
            from_date,
            datetime.time.min,
        )

        end_dt = datetime.datetime.combine(
            to_date + datetime.timedelta(days=1),
            datetime.time.min,
        )

        # Client was visited by one of supervisor's agents
        # during the requested date range.
        visited_exists = (
            select(1)
            .select_from(Visit)
            .where(
                Visit.outlet_ref == Client.id,
                Visit.agent_ref.in_(agent_ids),
                Visit.period >= start_dt,
                Visit.period < end_dt,
            )
            .exists()
        )

        # Client belongs to the supervisor's agents' coverage.
        #
        # We determine coverage from historical visits, because
        # Client._fld2267rref is not a reliable agent-assignment field.
        covered_by_agents_exists = (
            select(1)
            .select_from(Visit)
            .where(
                Visit.outlet_ref == Client.id,
                Visit.agent_ref.in_(agent_ids),
            )
            .exists()
        )

        result = await self.session.execute(
            select(
                func.count()
                .filter(visited_exists)
                .label("visited_clients"),

                func.count()
                .filter(~visited_exists)
                .label("not_visited_clients"),
            )
            .select_from(Client)
            .join(
                Territory,
                Territory.id == Client.territory_ref,
            )
            .where(
                Client.is_marked_for_deletion.is_(False),
                Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES),
                covered_by_agents_exists,
            )
        )

        row = result.one()

        return (
            row.visited_clients or 0,
            row.not_visited_clients or 0,
        )