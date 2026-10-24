"""Redis-backed cache for `/agent/stats`, refreshed by Celery - never by the
request path itself.

`sales_growth_cache` warms a small fixed set of keys (one per branch) on a
schedule. That doesn't fit here: agents are looked up by arbitrary id, not a
handful of branches, so there's no fixed list to warm proactively. Instead,
refresh is reactive: a cache miss still gets a live-computed answer (the
caller needs a response now), but the request handler never writes that
result to Redis. It only enqueues `refresh_agent_stats_cache` and returns -
the actual Redis write happens inside the Celery task, in the worker
process, not on the request path. The next request for that agent finds a
value the worker wrote, not one the request wrote.

The cache key is per agent only - NOT per `top_products_limit`. Header stats
(order_count, total_revenue, ...) don't depend on that parameter at all, and
the product list is cached once at `MAX_CACHED_TOP_PRODUCTS` and sliced down
to whatever the caller actually asked for. Keying by limit would mean every
distinct limit value is its own cache miss - e.g. a frontend "top N" selector
flipping between 5/10/20 would hit the database on every change, exactly the
problem this exists to avoid.
"""

import asyncio
import datetime
import json
import random
import time

import redis
from celery.signals import worker_ready
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from supervisor.src.core.celery_app import celery_app
from supervisor.src.core.config import DATABASE_URL, REDIS_URL
from supervisor.src.repositories.order import OrderRepository

CACHE_TTL_SECONDS = 30 * 60

# The sweep (see refresh_all_agent_stats_cache) reruns well inside the TTL, so
# a warmed entry is rewritten before it can expire - that, not a longer TTL, is
# what keeps the request path off the database. The TTL stays a safety net: if
# the worker stops, entries lapse after 30 min instead of serving stale numbers
# indefinitely.
SWEEP_INTERVAL_MINUTES = 20

# Sequential with a short pause between agents: ~750ms per agent in production
# x 289 agents spreads over ~4.6 min, and the pause keeps the sweep from
# monopolising a connection. Deliberately far smaller than the 5-10s used for
# the yearly sales-growth sweep, which has only 7 branches to get through - at
# 289 agents that spacing would overrun the interval.
AGENT_JITTER_RANGE_SECONDS = (0.1, 0.3)

# Guards against two sweeps overlapping (a slow run still going when beat fires
# the next one), which would double the database load for no benefit. Expires
# on its own so a crashed worker can't wedge the sweep permanently.
SWEEP_LOCK_KEY = "lock:agent_stats_sweep"
SWEEP_LOCK_TTL_SECONDS = 15 * 60

# Covers any top_products_limit up to this value from a single cached entry.
# A request above this cap still needs a live query for its product list
# (header stats never do) - raise this if the frontend's "top N" selector
# regularly goes higher.
MAX_CACHED_TOP_PRODUCTS = 20

# Belt-and-braces on top of the celery_app timeout settings: those are
# configuration Celery/kombu are supposed to honor, but investigating this
# exact call already turned up one path (the result backend's pubsub
# reconnect) that ignored the broker-level settings entirely and blocked far
# longer than configured. A hard wait_for here doesn't trust that every
# future Celery/kombu code path will honor conf settings correctly - it
# guarantees the ceiling regardless.
DISPATCH_TIMEOUT_SECONDS = 5

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


def agent_stats_cache_key(agent_id: bytes) -> str:
    return f"cache:agent_stats:{agent_id.hex()}"


def get_cached(key: str) -> dict | None:
    """Read helper for the request path - a Redis outage must degrade to a
    live query, never surface as a 500."""
    try:
        raw = _get_redis().get(key)
    except redis.RedisError:
        return None
    return json.loads(raw) if raw is not None else None


def _store(agent_id: bytes, payload: dict) -> None:
    _get_redis().set(
        agent_stats_cache_key(agent_id),
        json.dumps(payload, default=str), ex=CACHE_TTL_SECONDS,
    )


def cache_covers_limit(cached: dict, top_products_limit: int) -> bool:
    """Whether a cached entry can answer a request for `top_products_limit`
    products without a live query.

    True either because it already holds at least that many, or because it
    holds fewer than the cap - which only happens when the agent simply
    doesn't have that many distinct products, so a live query would find
    nothing more anyway.
    """
    products = cached.get("top_products") or []
    return top_products_limit <= len(products) or len(products) < MAX_CACHED_TOP_PRODUCTS


def _dispatch_refresh(agent_id: bytes) -> None:
    try:
        refresh_agent_stats_cache.delay(agent_id.hex())
    except Exception:
        # Broker down/unreachable - the next cache-miss request just tries
        # again. Losing one enqueue is fine; blocking on it is not.
        pass


async def trigger_refresh(agent_id: bytes) -> None:
    """Fire-and-forget dispatch from the request path.

    `.delay()` is a synchronous, blocking network call - even with the
    bounded socket timeouts set on `celery_app` (see core/celery_app.py),
    calling it directly inside an async endpoint would stall that request
    (and, since it blocks the event loop, every other concurrent request)
    for up to that timeout if the broker is slow. Run it in a thread instead,
    and call this via FastAPI's BackgroundTasks so it only runs after the
    response has already been sent - a slow or failed enqueue can never add
    latency to what the caller sees.
    """
    try:
        await asyncio.wait_for(
            asyncio.to_thread(_dispatch_refresh, agent_id),
            timeout=DISPATCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        # The underlying thread is left to finish on its own (there's no
        # way to cancel a blocking call already in flight) - this just stops
        # the background task itself from being the thing that hangs.
        pass


async def _compute(agent_id: bytes) -> dict:
    # Own short-lived engine - a Celery worker must not reuse asyncpg
    # connections across separate asyncio.run() calls.
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            repo = OrderRepository(session)
            stats, top_products = await repo.get_agent_stats_with_top_products(
                agent_id=agent_id, top_products_limit=MAX_CACHED_TOP_PRODUCTS)
            return {
                "order_count": stats.order_count,
                "total_revenue": stats.total_revenue or 0,
                "first_order": stats.first_order,
                "last_order": stats.last_order,
                "distinct_clients": stats.distinct_clients,
                "top_products": top_products,
            }
    finally:
        await engine.dispose()


@celery_app.task(name="supervisor.src.tasks.agent_stats_cache.refresh_agent_stats_cache")
def refresh_agent_stats_cache(agent_id_hex: str) -> None:
    agent_id = bytes.fromhex(agent_id_hex)
    payload = asyncio.run(_compute(agent_id))
    _store(agent_id, payload)


async def _cacheable_agent_ids() -> list[bytes]:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await OrderRepository(session).get_cacheable_agent_ids()
    finally:
        await engine.dispose()


@celery_app.task(name="supervisor.src.tasks.agent_stats_cache.refresh_all_agent_stats_cache")
def refresh_all_agent_stats_cache() -> int:
    """Keep every reachable agent's entry warm so the request path never has
    to compute one.

    Runs in the Celery worker, not the web process - warming costs the API
    nothing at startup or at any other time. Rewrites entries every
    SWEEP_INTERVAL_MINUTES, comfortably inside the 30-minute TTL, so a warmed
    agent never goes cold between sweeps.
    """
    redis_client = _get_redis()
    # SET NX EX: only one sweep holds this at a time, and it self-expires so a
    # killed worker can't block future sweeps.
    if not redis_client.set(SWEEP_LOCK_KEY, "1", nx=True, ex=SWEEP_LOCK_TTL_SECONDS):
        return 0

    try:
        agent_ids = asyncio.run(_cacheable_agent_ids())
        warmed = 0
        for index, agent_id in enumerate(agent_ids):
            try:
                payload = asyncio.run(_compute(agent_id))
                _store(agent_id, payload)
                warmed += 1
            except Exception:
                # One bad agent must not abandon the rest of the sweep.
                continue
            if index < len(agent_ids) - 1:
                time.sleep(random.uniform(*AGENT_JITTER_RANGE_SECONDS))
        return warmed
    finally:
        redis_client.delete(SWEEP_LOCK_KEY)


@worker_ready.connect
def _warm_cache_on_worker_start(sender=None, **kwargs):
    """Sweep immediately when the worker boots, rather than waiting up to
    SWEEP_INTERVAL_MINUTES for beat's next tick.

    Without this there's a window after every deploy - and after any Redis
    restart, since Redis runs without persistence - where the cache is empty
    and every request falls through to Postgres. Enqueued rather than run
    inline so the worker finishes starting up immediately; the sweep's own
    Redis lock keeps it from colliding with a beat tick that lands at the
    same moment.
    """
    try:
        refresh_all_agent_stats_cache.delay()
    except Exception:
        # Never block worker startup on this - beat will sweep shortly anyway.
        pass
