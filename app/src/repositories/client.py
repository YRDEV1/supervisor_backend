import datetime
import decimal

from sqlalchemy import exists
from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.client import Client
from app.src.models.territory import Territory
from app.src.models.client_transaction import ClientTransaction
from app.src.schemas.client import ClientType

class ClientRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_by_territory(self, territory_id: bytes, page: int, limit: int):
        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
        ).where(Client.territory_ref == territory_id).order_by(Client.code).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

    async def get_all(self, client_type: ClientType, page: int, limit: int, search: str | None = None):
        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
        ).join(Territory, Territory.id == Client.territory_ref).where(
            Client.is_marked_for_deletion == False, Territory.territory_name != "Тугатилганлар")

        if client_type == ClientType.AKB:
            recent_since = datetime.datetime.now() - datetime.timedelta(days=10)
            query = query.where(exists(
                select(1).where(ClientTransaction.client_ref == Client.id, ClientTransaction.period >= recent_since)
            ))

        query = query.order_by(Client.code)

        if not search:
            query = query.limit(limit).offset((page - 1) * limit)
            execution = await self.session.execute(query)
            return execution.all()

        execution = await self.session.execute(query)
        rows = execution.all()
        lowered = search.lower()
        code_match = decimal.Decimal(search) if search.isdigit() else None
        rows = [
            row for row in rows
            if lowered in row.client_name.lower() or lowered in row.phone.lower()
            or (code_match is not None and row.code == code_match)
        ]
        start = (page - 1) * limit
        return rows[start:start + limit]

    async def get_by_agent(self, agent_id: bytes, page: int, limit: int):
        query = select(
            Client.id,
            Client.code,
            Client.full_name.label("client_name"),
            Client.phone,
        ).where(Client.agent_ref == agent_id).order_by(Client.code).limit(limit).offset((page - 1) * limit)
        execution = await self.session.execute(query)
        return execution.all()

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
