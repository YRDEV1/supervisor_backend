from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from agents.src.core.config import settings


class OnecBase(DeclarativeBase):
    pass


# Read-only, 30s query limit
onec_engine = create_async_engine(
    settings.onec_database_url,
    pool_pre_ping=True,
    connect_args={"server_settings": {"default_transaction_read_only": "on", "statement_timeout": "30000"}},
)
onec_session_factory = async_sessionmaker(onec_engine, expire_on_commit=False)


async def get_onec_db_session() -> AsyncIterator[AsyncSession]:
    async with onec_session_factory() as session:
        yield session


ONEC_DB_SESSION = Annotated[AsyncSession, Depends(get_onec_db_session)]
