from sqlalchemy import delete, insert, select, update

from agents.src.core.database import DB_SESSION
from agents.src.models.agent import Agent


class AgentRepository:
    def __init__(self, db: DB_SESSION):
        self.db = db

    async def get_all(self, offset: int, limit: int):
        query = select(Agent).order_by(Agent.id).offset(offset).limit(limit)
        execution = await self.db.execute(query)
        return execution.scalars().all()

    async def get_all_by_supervisor_id(self, supervisor_id: bytes, offset: int, limit: int):
        query = (
            select(Agent)
            .where(Agent.supervisor_id == supervisor_id)
            .order_by(Agent.id)
            .offset(offset)
            .limit(limit)
        )
        execution = await self.db.execute(query)
        return execution.scalars().all()

    async def get_agent_by_id(self, agent_id: int):
        query = select(Agent).where(Agent.id == agent_id)
        execution = await self.db.execute(query)
        return execution.scalar_one_or_none()

    async def get_agent_by_name(self, agent_name: str):
        query = select(Agent).where(Agent.agent_name == agent_name)
        execution = await self.db.execute(query)
        return execution.scalar_one_or_none()

    async def create_agent(self, payload: dict):
        query = insert(Agent).values(payload).returning(Agent)
        execution = await self.db.execute(query)
        await self.db.commit()
        return execution.scalar_one()

    async def update_agent(self, agent_id: int, payload: dict):
        query = update(Agent).where(Agent.id == agent_id).values(payload).returning(Agent)
        execution = await self.db.execute(query)
        await self.db.commit()
        return execution.scalar_one()

    async def delete_agent(self, agent_id: int):
        query = delete(Agent).where(Agent.id == agent_id)
        await self.db.execute(query)
        await self.db.commit()
