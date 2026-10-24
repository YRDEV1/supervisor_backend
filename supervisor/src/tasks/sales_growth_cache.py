"""Redis-backed cache for `/product/sales-growth`, refreshed by Celery.

The endpoint's four buckets have very different costs: daily/weekly/monthly
each scan ~2 months of line items (~1s together), while the yearly bucket spans
two calendar years and measured ~3.8s on its own. They are therefore cached
under separate keys on separate schedules:

    short  (daily/weekly/monthly)  refresh every 20min, TTL 30min
    yearly                         refresh every 24h,   TTL 26h

In both cases the TTL is longer than the refresh interval on purpose - a failed
run leaves the previous value in place instead of dropping every request back
onto a live aggregate.

Keys carry the reference date, so a caller asking for an arbitrary date gets a
cache entry of its own rather than falling through to a live query every time.
Celery keeps "today" warm; other dates are filled in on first request and then
served from cache. A bucket whose period has already closed can never change
again, so those entries get a much longer TTL - see `short_ttl`/`yearly_ttl`.
"""

import asyncio
import datetime
import json
import random
import time

import redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from supervisor.src.core.celery_app import celery_app
from supervisor.src.core.config import DATABASE_URL, REDIS_URL
from supervisor.src.repositories.employee import EmployeeRepository
from supervisor.src.repositories.product import ProductRepository
from supervisor.src.core.types import TASHKENT_TZ

SHORT_CACHE_TTL_SECONDS = 30 * 60
YEARLY_CACHE_TTL_SECONDS = 26 * 60 * 60
# A period that has already ended is immutable - no refresh can change it, so
# these entries only need to expire to stop the keyspace growing forever.
CLOSED_PERIOD_TTL_SECONDS = 30 * 24 * 60 * 60

# Gap between consecutive branches in the yearly sweep. Each branch's yearly
# aggregate is the heaviest query in the app, so they run one at a time with a
# pause in between rather than back-to-back.
YEARLY_JITTER_RANGE_SECONDS = (5, 10)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        # Bounded timeouts, not just "connection refused" - a network
        # partition (packets silently dropped, not rejected) would otherwise
        # hang the read on the request path indefinitely.
        _redis_client = redis.from_url(
            REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    return _redis_client


def short_cache_key(branch_id: bytes, day: datetime.date) -> str:
    """Daily/weekly/monthly buckets all shift day by day, so the key is dated."""
    return f"cache:sales_growth:short:{branch_id.hex()}:{day.isoformat()}"


def yearly_cache_key(branch_id: bytes, year: int) -> str:
    """The yearly bucket only depends on which calendar year the reference date
    falls in, so keying it by year avoids 365 identical entries per branch."""
    return f"cache:sales_growth:yearly:{branch_id.hex()}:{year}"


def _next_month(date: datetime.date) -> datetime.date:
    return date.replace(year=date.year + 1, month=1, day=1) if date.month == 12 \
        else date.replace(month=date.month + 1, day=1)


def short_ttl(reference_date: datetime.datetime, now: datetime.datetime) -> int:
    """Month is the widest bucket in the short set; once it has ended, none of
    daily/weekly/monthly for that date can change again."""
    month_end = _next_month(reference_date.date().replace(day=1))
    return CLOSED_PERIOD_TTL_SECONDS if month_end <= now.date() else SHORT_CACHE_TTL_SECONDS


def yearly_ttl(reference_date: datetime.datetime, now: datetime.datetime) -> int:
    year_end = datetime.date(reference_date.year + 1, 1, 1)
    return CLOSED_PERIOD_TTL_SECONDS if year_end <= now.date() else YEARLY_CACHE_TTL_SECONDS


def get_cached(key: str) -> dict | None:
    """Read helper for the request path - a Redis outage must degrade to a live
    query, never surface as a 500."""
    try:
        raw = _get_redis().get(key)
    except redis.RedisError:
        return None
    return json.loads(raw) if raw is not None else None


def set_cached(key: str, payload: dict, ttl_seconds: int) -> None:
    """Write-through helper. Also used from the request path, so a Redis outage
    must not fail the response that was otherwise computed successfully."""
    try:
        _get_redis().set(key, json.dumps(payload, default=str), ex=ttl_seconds)
    except redis.RedisError:
        pass


async def _with_session(handler):
    # A Celery worker must not reuse asyncpg connections across separate
    # asyncio.run() calls, so each task run owns its engine and disposes it.
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await handler(session)
    finally:
        await engine.dispose()


async def _branch_refs(session) -> list[bytes]:
    return await EmployeeRepository(session).get_supervisor_branch_refs()


@celery_app.task(name="supervisor.src.tasks.sales_growth_cache.refresh_short_sales_growth_cache")
def refresh_short_sales_growth_cache() -> int:
    """Daily/weekly/monthly buckets for every supervised branch, for today.
    Cheap enough to run straight through without staggering."""

    async def handler(session):
        repo = ProductRepository(session)
        # DB columns are naive local (Tashkent) time - a tz-aware value here
        # errors against them outright (see supervisor/src/endoints/product.py).
        now = datetime.datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        refreshed = 0
        for branch_id in await _branch_refs(session):
            payload = await repo.get_short_sales_growth(reference_date=now, branch_id=branch_id)
            set_cached(short_cache_key(branch_id, now.date()), payload, short_ttl(now, now))
            refreshed += 1
        return refreshed

    return asyncio.run(_with_session(handler))


@celery_app.task(name="supervisor.src.tasks.sales_growth_cache.refresh_yearly_sales_growth_cache")
def refresh_yearly_sales_growth_cache() -> int:
    """Yearly bucket for every supervised branch, computed strictly one at a
    time: a branch's aggregate is written before the next one starts, then a
    random 5-10s pause separates them. Two branches never hold a two-year
    aggregate open against Postgres simultaneously.
    """

    async def handler(session):
        repo = ProductRepository(session)
        # Naive Tashkent time, consistent with refresh_short_sales_growth_cache
        # above - not relying on the host's system timezone matching.
        now = datetime.datetime.now(TASHKENT_TZ).replace(tzinfo=None)
        branch_refs = await _branch_refs(session)
        refreshed = 0
        for index, branch_id in enumerate(branch_refs):
            payload = await repo.get_yearly_sales_growth(reference_date=now, branch_id=branch_id)
            set_cached(yearly_cache_key(branch_id, now.year), payload, yearly_ttl(now, now))
            refreshed += 1
            if index < len(branch_refs) - 1:
                # Blocking sleep is intentional: it must hold this worker slot
                # so the next branch genuinely starts later, not concurrently.
                time.sleep(random.uniform(*YEARLY_JITTER_RANGE_SECONDS))
        return refreshed

    return asyncio.run(_with_session(handler))
