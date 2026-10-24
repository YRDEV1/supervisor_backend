import datetime
import decimal

from sqlalchemy import func
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.core.sales_trend import count_working_days, is_working_day, month_bounds, required_target
from supervisor.src.models.employee import Employee, ROLE_SALES_REP
from supervisor.src.models.plan import PlanDocument, PlanLineItem, MonthlySalesRecord

ZERO = decimal.Decimal(0)

# Daily granularity's hourly series never starts earlier than this, whether
# from a real shift-time or the no-data fallback.
DAILY_FALLBACK_START_HOUR = 5

class SalesTrendRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_team_plan(self, agent_ids: list[bytes], as_of: datetime.date, branch_id: bytes) -> decimal.Decimal:
        """Sum of each agent's most recent plan amount dated on or before
        `as_of` - "as of" because plans persist across months until revised
        (see models/plan.py), so the right lookup for "the plan for month M"
        is the latest row at or before M's end, not a row dated inside M.

        Agents with no plan doc at all contribute 0, not an error - only 125
        of ~289 agents have ever had one (checked live).

        Restricted to posted, non-deleted plan docs for `ТП`-role, non-deleted
        agents, issued for the caller's own branch - without this, `agent_ids`
        (built from the visit register, any role) can include a bad/unposted
        record: one live example was a `100,000,000,000` (100 billion) plan
        line under a `ТМ`-role account, ~100x every real value; the branch
        filter guards against picking up a plan doc issued for a different
        branch (e.g. an agent visited across branches) - see
        DATA/SALE_TREND.md's "Monthly plan at branch level" section, which
        documents both guards.
        """
        if not agent_ids:
            return decimal.Decimal(0)

        as_of_dt = datetime.datetime.combine(as_of, datetime.time.max)
        # DISTINCT ON (Postgres): one row per agent, the latest by document
        # date - same pattern as AgentTerritoryRepository.get_agent_territories.
        latest_per_agent = select(
            PlanLineItem.agent_ref, PlanLineItem.plan_amount,
        ).select_from(PlanLineItem).join(
            PlanDocument, PlanDocument.id == PlanLineItem.document_ref
        ).where(
            PlanLineItem.agent_ref.in_(agent_ids), PlanDocument.date_time <= as_of_dt,
            PlanDocument.is_posted == True, PlanDocument.is_marked_for_deletion == False,
            PlanDocument.branch_ref == branch_id,
        ).distinct(PlanLineItem.agent_ref).order_by(
            PlanLineItem.agent_ref, PlanDocument.date_time.desc()
        ).subquery()

        query = select(func.coalesce(func.sum(latest_per_agent.c.plan_amount), 0)).select_from(
            latest_per_agent
        ).join(Employee, Employee.id == latest_per_agent.c.agent_ref).where(
            Employee.parent_id == ROLE_SALES_REP.bytes,
            Employee.is_marked_for_deletion == False,
        )
        return (await self.session.execute(query)).scalar_one()

    async def get_bucketed_actual(self, agent_ids: list[bytes], bucket: str,
                                   start: datetime.datetime, end: datetime.datetime) -> dict[datetime.datetime, decimal.Decimal]:
        """Actual revenue for the team, grouped by `bucket` (a Postgres
        date_trunc field: 'hour', 'day', or 'month'), over [start, end)."""
        if not agent_ids:
            return {}
        bucket_start = func.date_trunc(bucket, MonthlySalesRecord.period).label("bucket_start")
        query = select(
            bucket_start, func.sum(MonthlySalesRecord.amount).label("amount"),
        ).where(
            MonthlySalesRecord.agent_ref.in_(agent_ids),
            MonthlySalesRecord.period >= start, MonthlySalesRecord.period < end,
        ).group_by(bucket_start)
        rows = (await self.session.execute(query)).all()
        return {row.bucket_start: row.amount for row in rows}

    async def get_total_actual(self, agent_ids: list[bytes],
                                start: datetime.datetime, end: datetime.datetime) -> decimal.Decimal:
        """Unbucketed total - used for month/year-to-date cumulative sums."""
        if not agent_ids:
            return decimal.Decimal(0)
        query = select(func.coalesce(func.sum(MonthlySalesRecord.amount), 0)).where(
            MonthlySalesRecord.agent_ref.in_(agent_ids),
            MonthlySalesRecord.period >= start, MonthlySalesRecord.period < end,
        )
        return (await self.session.execute(query)).scalar_one()

    # ------------------------------------------------------------------
    # Granularity-specific point series. Each combines the queries above
    # with the pure formula in supervisor/src/core/sales_trend - see that module's
    # docstring for the general rule every one of these implements.
    # ------------------------------------------------------------------

    async def get_daily_trend(self, agent_ids: list[bytes], reference_date: datetime.date,
                               shift_start: datetime.time, shift_end: datetime.time,
                               branch_id: bytes) -> list[dict]:
        """One point per hour of the team's shift window. Target formula
        (requirements doc section 4) is scoped to the DAILY plan, unlike
        weekly/monthly which target the monthly plan - see that section for
        why: a day's own remaining hours vs. its own remaining plan."""
        day_start = datetime.datetime.combine(reference_date, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)

        first_hour, last_hour = shift_start.hour, shift_end.hour + (1 if shift_end.minute else 0)
        if last_hour <= first_hour:
            # Degenerate/missing shift data - fall back to a full business
            # day rather than emit zero points. Checked live: every employee
            # row currently has 0001-01-01 00:00 for both shift fields (see
            # get_sales_trend's caller comment), so this is the path actually
            # exercised today, not a rare edge case.
            first_hour, last_hour = DAILY_FALLBACK_START_HOUR, 24
        # Even with real shift data, don't start counting before this hour -
        # a day's series beginning at midnight isn't meaningful for a sales
        # team regardless of what a shift-time field says.
        first_hour = max(first_hour, DAILY_FALLBACK_START_HOUR)
        hours = list(range(first_hour, last_hour))

        bucketed = await self.get_bucketed_actual(agent_ids, "hour", day_start, day_end)

        month_start, month_end = month_bounds(reference_date)
        monthly_plan = await self.get_team_plan(agent_ids, as_of=reference_date, branch_id=branch_id)
        total_working_days = count_working_days(month_start, month_end)
        daily_plan = (monthly_plan / total_working_days) if total_working_days else ZERO
        # Sunday - requirements doc section 7: planned_revenue = 0, and it's
        # excluded from the working-day count on every other day's calc too.
        if not is_working_day(reference_date):
            daily_plan = ZERO

        points = []
        cumulative = ZERO
        for index, hour in enumerate(hours):
            bucket_start = day_start.replace(hour=hour)
            actual = bucketed.get(bucket_start, ZERO)
            cumulative += actual
            remaining_hours = len(hours) - index - 1
            target = required_target(daily_plan, cumulative, remaining_hours)
            points.append({
                "label": bucket_start.strftime("%H:%M"),
                "period_start": bucket_start,
                "actual_revenue": actual,
                "target_revenue": target,
            })
        return points

    async def _day_points(self, agent_ids: list[bytes], days: list[datetime.date],
                           monthly_plan: decimal.Decimal, month_start: datetime.date,
                           month_end: datetime.date, label_format: str) -> list[dict]:
        """Shared by weekly and monthly - both target the monthly plan
        (requirements doc section 5: "dynamic target oylik plan asosida
        hisoblanadi"), they only differ in which days are shown."""
        first_day_start = datetime.datetime.combine(days[0], datetime.time.min)
        last_day_end = datetime.datetime.combine(days[-1] + datetime.timedelta(days=1), datetime.time.min)
        bucketed = await self.get_bucketed_actual(agent_ids, "day", first_day_start, last_day_end)

        # Cumulative must be month-to-date, not just the displayed window -
        # a week starting mid-month still needs the earlier days' actual to
        # compute a correct remaining_plan.
        cumulative = await self.get_total_actual(
            agent_ids, datetime.datetime.combine(month_start, datetime.time.min), first_day_start)

        points = []
        for day in days:
            bucket_start = datetime.datetime.combine(day, datetime.time.min)
            actual = bucketed.get(bucket_start, ZERO)
            cumulative += actual
            remaining_working_days = count_working_days(day + datetime.timedelta(days=1), month_end)
            target = required_target(monthly_plan, cumulative, remaining_working_days)
            points.append({
                "label": day.strftime(label_format),
                "period_start": bucket_start,
                "actual_revenue": actual,
                "target_revenue": target,
            })
        return points

    async def get_weekly_trend(self, agent_ids: list[bytes], reference_date: datetime.date,
                                branch_id: bytes) -> list[dict]:
        """One point per day, Monday-Sunday, for the week containing
        reference_date. Simplifying assumption: the monthly plan/cumulative
        used for the target formula is scoped to reference_date's own month
        even when the displayed week spans a month boundary."""
        week_start = reference_date - datetime.timedelta(days=reference_date.weekday())
        days = [week_start + datetime.timedelta(days=i) for i in range(7)]
        month_start, month_end = month_bounds(reference_date)
        monthly_plan = await self.get_team_plan(agent_ids, as_of=reference_date, branch_id=branch_id)
        return await self._day_points(agent_ids, days, monthly_plan, month_start, month_end, "%a")

    async def get_month_required_target(self, agent_ids: list[bytes], reference_date: datetime.date,
                                         branch_id: bytes) -> decimal.Decimal:
        """Dynamic remaining-target for reference_date's month - same formula
        as the monthly trend's points (requirements doc section 12: target is
        always the amount still needed, recomputed from actual progress), but
        collapsed to one number instead of a per-day series. Used by
        GET /order/all's `target` field, which previously returned the raw
        monthly plan sum unchanged - so it looked identical for any date/range
        picked within a month with no new plan filed since."""
        month_start, month_end = month_bounds(reference_date)
        monthly_plan = await self.get_team_plan(agent_ids, as_of=reference_date, branch_id=branch_id)
        cumulative_actual = await self.get_total_actual(
            agent_ids, datetime.datetime.combine(month_start, datetime.time.min),
            datetime.datetime.combine(reference_date + datetime.timedelta(days=1), datetime.time.min))
        remaining_working_days = count_working_days(reference_date + datetime.timedelta(days=1), month_end)
        return required_target(monthly_plan, cumulative_actual, remaining_working_days)

    async def get_monthly_trend(self, agent_ids: list[bytes], reference_date: datetime.date,
                                 branch_id: bytes) -> list[dict]:
        """One point per calendar day of reference_date's month."""
        month_start, month_end = month_bounds(reference_date)
        days = [month_start + datetime.timedelta(days=i) for i in range((month_end - month_start).days)]
        monthly_plan = await self.get_team_plan(agent_ids, as_of=reference_date, branch_id=branch_id)
        return await self._day_points(agent_ids, days, monthly_plan, month_start, month_end, "%Y-%m-%d")

    async def get_yearly_trend(self, agent_ids: list[bytes], reference_date: datetime.date,
                                branch_id: bytes) -> list[dict]:
        """One point per month of reference_date's year. annual_plan is the
        sum of each month's OWN plan (requirements doc section 10), looked up
        as of that specific month's end - not today's plan repeated 12x -
        since a plan can be revised between months."""
        year = reference_date.year
        month_starts = [datetime.date(year, m, 1) for m in range(1, 13)]

        monthly_plans = []
        for index, m_start in enumerate(month_starts):
            _, m_end = month_bounds(m_start)
            monthly_plans.append(await self.get_team_plan(
                agent_ids, as_of=m_end - datetime.timedelta(days=1), branch_id=branch_id))
        annual_plan = sum(monthly_plans, ZERO)

        year_start = datetime.datetime(year, 1, 1)
        next_year_start = datetime.datetime(year + 1, 1, 1)
        bucketed = await self.get_bucketed_actual(agent_ids, "month", year_start, next_year_start)

        points = []
        cumulative = ZERO
        for index, m_start in enumerate(month_starts):
            bucket_start = datetime.datetime.combine(m_start, datetime.time.min)
            actual = bucketed.get(bucket_start, ZERO)
            cumulative += actual
            remaining_months = 12 - (index + 1)
            target = required_target(annual_plan, cumulative, remaining_months)
            points.append({
                "label": m_start.strftime("%Y-%m"),
                "period_start": bucket_start,
                "actual_revenue": actual,
                "target_revenue": target,
            })
        return points

    # ------------------------------------------------------------------
    # Branch-level monthly plan - DATA/SALE_TREND.md's "Monthly plan at
    # branch level (not just per-agent)" section. Distinct from
    # get_team_plan/get_month_team_plan above, which scope to one
    # supervisor's own visited-agent team: this scopes to every `ТП` agent
    # on a branch, regardless of which supervisor (if any) has visited them.
    # ------------------------------------------------------------------

    def _latest_branch_plan_per_agent(self, branch_id: bytes, month_end: datetime.date):
        """Each agent's most recent POSTED, non-deleted plan doc for this
        branch dated before month_end - not "dated inside the month," since
        plans persist unchanged until revised (see models/plan.py)."""
        month_end_dt = datetime.datetime.combine(month_end, datetime.time.min)
        return select(
            PlanLineItem.agent_ref, PlanLineItem.plan_amount,
            PlanDocument.date_time.label("plan_set_at"),
        ).distinct(PlanLineItem.agent_ref).select_from(PlanLineItem).join(
            PlanDocument, PlanDocument.id == PlanLineItem.document_ref
        ).where(
            PlanDocument.branch_ref == branch_id,
            PlanDocument.date_time < month_end_dt,
            PlanDocument.is_posted == True,
            PlanDocument.is_marked_for_deletion == False,
        ).order_by(PlanLineItem.agent_ref, PlanDocument.date_time.desc())

    async def get_branch_monthly_plan(self, branch_id: bytes, month_end: datetime.date) -> decimal.Decimal:
        """Sum of the branch's `ТП` agents' latest plan-as-of-date. Verified
        against branch Шерин, August 2026: query returned 10,174,335,614
        against a target of ~10,101,000,000 (within 0.7%)."""
        latest = self._latest_branch_plan_per_agent(branch_id, month_end).subquery()
        query = select(func.coalesce(func.sum(latest.c.plan_amount), 0)).select_from(latest).join(
            Employee, Employee.id == latest.c.agent_ref
        ).where(
            Employee.parent_id == ROLE_SALES_REP.bytes,
            Employee.is_marked_for_deletion == False,
        )
        return (await self.session.execute(query)).scalar_one()

    async def get_branch_plan_breakdown(self, branch_id: bytes, month_end: datetime.date) -> list[dict]:
        """One row per `ТП` agent contributing to the branch total above,
        highest plan first - for a plan-breakdown display."""
        latest = self._latest_branch_plan_per_agent(branch_id, month_end).subquery()
        query = select(
            Employee.code.label("agent_code"), Employee.full_name.label("agent_name"),
            latest.c.plan_amount, latest.c.plan_set_at,
        ).select_from(latest).join(Employee, Employee.id == latest.c.agent_ref).where(
            Employee.parent_id == ROLE_SALES_REP.bytes,
            Employee.is_marked_for_deletion == False,
        ).order_by(latest.c.plan_amount.desc())
        rows = (await self.session.execute(query)).all()
        return [
            {
                "agent_code": row.agent_code, "agent_name": row.agent_name,
                "plan_amount": row.plan_amount, "plan_set_at": row.plan_set_at,
            }
            for row in rows
        ]
