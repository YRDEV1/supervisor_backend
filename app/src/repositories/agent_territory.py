from sqlalchemy.future import select

from app.src.core.database import ASYNC_SESSION
from app.src.models.visit import Visit
from app.src.models.client import Client
from app.src.models.territory import Territory

class AgentTerritoryRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_agent_territories(self, agent_id: bytes):
        query = select(
            Territory.id,
            Territory.territory_name,
        ).distinct(Territory.id).select_from(Visit).join(Client, Client.id == Visit.outlet_ref).join(
            Territory, Territory.id == Client.territory_ref
        ).where(Visit.agent_ref == agent_id).order_by(Territory.id)
        execution = await self.session.execute(query)
        return execution.all()
