"""Plan-vs-actual calculation logic for `GET /product/sales-trend`.

Implements the formula added to supervisor_backend_requirements.md section
2.3 verbatim - see that file for the worked examples this was checked
against. No I/O here: callers already have plan/actual figures from the DB,
this module is only the arithmetic and the Sunday-aware calendar counting.

The general rule (requirements doc section 13/15), used by every
granularity with a different `remaining_periods` definition:

    remaining_plan   = total_plan - cumulative_actual
    required_target  = remaining_plan / remaining_periods

`target` is always the requirement for the *next* period, not the current
one (section 12) - a point's `target_revenue` answers "what was needed after
this point," reconstructed the same way regardless of whether the point is
in the past or is the latest one.
"""

import datetime
import decimal

ZERO = decimal.Decimal(0)


def is_working_day(date: datetime.date) -> bool:
    """Sunday is the only non-working day - requirements doc section 7
    ("31 calendar days, 28 working days, 3 Sundays")."""
    return date.weekday() != 6  # Monday=0 ... Sunday=6


def count_working_days(start: datetime.date, end_exclusive: datetime.date) -> int:
    """Working (non-Sunday) days in the half-open range [start, end_exclusive)."""
    total_days = (end_exclusive - start).days
    return sum(
        1 for offset in range(total_days)
        if is_working_day(start + datetime.timedelta(days=offset))
    )


def next_working_day(date: datetime.date) -> datetime.date:
    candidate = date + datetime.timedelta(days=1)
    while not is_working_day(candidate):
        candidate += datetime.timedelta(days=1)
    return candidate


def month_bounds(date: datetime.date) -> tuple[datetime.date, datetime.date]:
    """(first day of date's month, first day of the following month)."""
    start = date.replace(day=1)
    end = datetime.date(start.year + 1, 1, 1) if start.month == 12 else start.replace(month=start.month + 1)
    return start, end


def required_target(total_plan: decimal.Decimal, cumulative_actual: decimal.Decimal,
                     remaining_periods: int) -> decimal.Decimal:
    """remaining_plan / remaining_periods - zero once the plan is already met
    (section 8), no periods remain (section 9's boundary), or the team has no
    plan at all (no agent has ever filed one - total_plan is the plain sum
    of each agent's most recent plan doc, so this is 0 exactly when none
    exists, matching a literal reading of "sum the agents' plans")."""
    remaining_plan = total_plan - cumulative_actual
    if remaining_plan <= ZERO or remaining_periods <= 0:
        return ZERO
    return remaining_plan / remaining_periods
