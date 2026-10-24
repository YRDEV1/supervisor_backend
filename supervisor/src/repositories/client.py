import datetime
import decimal

from sqlalchemy import cast, exists, or_, String, tuple_
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.client import Client
from supervisor.src.models.territory import Territory, EXCLUDED_TERRITORY_NAMES
from supervisor.src.models.client_transaction import ClientTransaction
from supervisor.src.schemas.client import ClientType
from supervisor.src.core.types import TASHKENT_TZ

CLIENT_COLUMNS = (
    Client.id,
    Client.code,
    Client.full_name.label("client_name"),
    Client.phone,
)

def _paginate_by_code(query, limit: int, cursor: tuple[decimal.Decimal, bytes] | None):
    """Keyset page over `ORDER BY code, id`, fetching one extra row so the
    caller can tell whether a further page exists without a COUNT."""
    if cursor is not None:
        query = query.where(tuple_(Client.code, Client.id) > tuple_(*cursor))
    return query.order_by(Client.code, Client.id).limit(limit + 1)

class ClientRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def _fetch_page(self, query, limit: int, cursor):
        rows = (await self.session.execute(_paginate_by_code(query, limit, cursor))).all()
        return rows[:limit], len(rows) > limit

    async def get_by_territory(self, territory_id: bytes, limit: int,
                                cursor: tuple[decimal.Decimal, bytes] | None = None):
        query = select(*CLIENT_COLUMNS).where(Client.territory_ref == territory_id)
        return await self._fetch_page(query, limit, cursor)

    async def get_all(self, client_type: ClientType, limit: int, search: str | None = None,
                       cursor: tuple[decimal.Decimal, bytes] | None = None):
        query = select(*CLIENT_COLUMNS).join(Territory, Territory.id == Client.territory_ref).where(
            Client.is_marked_for_deletion == False,
            Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES))

        if client_type == ClientType.AKB:
            # Naive Tashkent time - DB columns are naive local time, and a
            # tz-aware value errors against them outright (see
            # supervisor/src/endoints/product.py for the same class of bug).
            recent_since = datetime.datetime.now(TASHKENT_TZ).replace(tzinfo=None) - datetime.timedelta(days=10)
            query = query.where(exists(
                select(1).where(ClientTransaction.client_ref == Client.id, ClientTransaction.period >= recent_since)
            ))

        if search:
            # Filtered in Postgres, not in Python - the previous version pulled
            # every client row into the process before slicing, which also made
            # the page size meaningless as a query bound. Unlike `=`/`!=`,
            # there is no `mvarchar ~~* mvarchar` ILIKE operator at all on this
            # DB export - even both sides typed MVARCHAR fails - so ILIKE
            # still needs the column cast to a real text type explicitly.
            pattern = f"%{search}%"
            conditions = [cast(Client.full_name, String).ilike(pattern), cast(Client.phone, String).ilike(pattern)]
            if search.isdigit():
                conditions.append(Client.code == decimal.Decimal(search))
            query = query.where(or_(*conditions))

        return await self._fetch_page(query, limit, cursor)

    async def get_by_agent(self, agent_id: bytes, limit: int,
                            cursor: tuple[decimal.Decimal, bytes] | None = None):
        query = select(*CLIENT_COLUMNS).where(Client.agent_ref == agent_id)
        return await self._fetch_page(query, limit, cursor)

    async def get_by_id(self, client_id: bytes):
        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
            Client.latitude,
            Client.longitude,
        ).where(Client.id == client_id)
        execution = await self.session.execute(query)
        return execution.one_or_none()
