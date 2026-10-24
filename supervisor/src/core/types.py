import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import AfterValidator


def _strip_tz(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is not None:
        return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return value


# DB columns are all TIMESTAMP WITHOUT TIME ZONE - asyncpg rejects comparing
# tz-aware datetimes against them. Query params can arrive tz-aware (e.g. a
# trailing "Z"), so normalize to naive UTC after Pydantic parses the string.
NaiveDatetime = Annotated[datetime.datetime, AfterValidator(_strip_tz)]

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")