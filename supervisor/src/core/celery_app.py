from celery import Celery
from celery.schedules import crontab

from supervisor.src.core.config import REDIS_URL

celery_app = Celery(
    "supervisor_backend",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["supervisor.src.tasks.sales_growth_cache", "supervisor.src.tasks.agent_stats_cache"],
)

celery_app.conf.timezone = "UTC"

# task_publish_retry defaults to on with a policy of ~3 retries, and the
# transport itself has no socket timeout unless set here - together that lets
# a single blocked `.delay()` call (e.g. broker unreachable during a Redis
# restart) stall for a long time. Callers that dispatch from the request path
# (see supervisor/src/tasks/agent_stats_cache.trigger_refresh) need this to fail
# within ~2s, not retry-and-hang, since a slow enqueue must never turn into a
# slow HTTP response.
celery_app.conf.broker_transport_options = {
    "socket_connect_timeout": 2,
    "socket_timeout": 2,
    "retry_on_timeout": False,
    "max_retries": 0,
}
celery_app.conf.task_publish_retry = False
# Separate from task_publish_retry above: this governs retrying the broker
# TCP connection itself. Left at its default, a refused connection retries
# dozens of times with growing backoff before giving up - the socket-level
# timeouts above never get a chance to matter.
celery_app.conf.broker_connection_retry = False
celery_app.conf.broker_connection_retry_on_startup = False
# None of these tasks are ever awaited via .get()/AsyncResult - they're all
# fire-and-forget cache refreshes. Without this, `.delay()` still registers
# for a result behind the scenes, which opens a *separate* pubsub connection
# to the result backend with its own retry loop - one with no relationship
# to the broker settings above, and no bounded timeout at all. Confirmed via
# a hung stack trace landing in celery/backends/redis.py:_reconnect_pubsub
# rather than anything broker-related. This is what actually made a
# request-path `.delay()` call unkillable when Redis was down - the broker
# timeouts above were real but irrelevant to the actual hang.
celery_app.conf.task_ignore_result = True

# Each TTL is longer than its refresh interval on purpose, so one failed run
# leaves the previous value in place instead of dropping traffic onto a live
# aggregate. The yearly bucket is ~4x the cost of the other three combined, so
# it runs on its own daily cycle instead of every 6h.
celery_app.conf.beat_schedule = {
    # daily/weekly/monthly - every 20 min, TTL 30 min (today's revenue moves
    # throughout the day; a closed period still gets the long TTL - see
    # short_ttl in tasks/sales_growth_cache.py)
    "refresh-short-sales-growth-cache": {
        "task": "supervisor.src.tasks.sales_growth_cache.refresh_short_sales_growth_cache",
        "schedule": crontab(minute="*/20"),
    },
    # yearly - once a day at 02:00, TTL 26h
    "refresh-yearly-sales-growth-cache": {
        "task": "supervisor.src.tasks.sales_growth_cache.refresh_yearly_sales_growth_cache",
        "schedule": crontab(minute=0, hour=2),
    },
    # Every active agent's /agent/stats entry, every 20 min against a 30 min
    # TTL - rewritten before it can expire, so the request path never has to
    # compute one. See SWEEP_INTERVAL_MINUTES in tasks/agent_stats_cache.py.
    "refresh-all-agent-stats-cache": {
        "task": "supervisor.src.tasks.agent_stats_cache.refresh_all_agent_stats_cache",
        "schedule": crontab(minute="*/20"),
    },
}
