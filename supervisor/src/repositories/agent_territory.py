from sqlalchemy import or_
from sqlalchemy.future import select

from supervisor.src.core.database import ASYNC_SESSION
from supervisor.src.models.visit import Visit
from supervisor.src.models.client import Client
from supervisor.src.models.territory import Territory, EXCLUDED_TERRITORY_NAMES

class AgentTerritoryRepository:
    def __init__(self, session: ASYNC_SESSION):
        self.session = session

    async def get_agent_territories(self, agent_id: bytes):
        query = select(
            Territory.id,
            Territory.territory_name,
        ).distinct(Territory.id).select_from(Visit).outerjoin(Client, Client.id == Visit.outlet_ref).outerjoin(
            Territory, Territory.id == Client.territory_ref
        ).where(
            Visit.agent_ref == agent_id,
            # outerjoin can leave Territory NULL (visit with no linked
            # client/territory) - notin_ alone would drop those rows since
            # NULL comparisons are neither true nor false, so a visit with
            # no territory must be let through explicitly.
            or_(Territory.territory_name.notin_(EXCLUDED_TERRITORY_NAMES), Territory.territory_name.is_(None)),
        ).order_by(Territory.id)
        execution = await self.session.execute(query)
        return execution.all()
