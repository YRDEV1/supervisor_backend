import asyncio

from fastapi import Depends
from collections.abc import AsyncGenerator
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import Annotated

from supervisor.src.core.config import DATABASE_URL

class Base(DeclarativeBase):
    pass

# Explicit so `warm_pool` below opens exactly this many connections - matches
# SQLAlchemy's own defaults, just no longer implicit.
POOL_SIZE = 5
MAX_OVERFLOW = 10

engine = create_async_engine(DATABASE_URL, pool_size=POOL_SIZE, max_overflow=MAX_OVERFLOW)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

ASYNC_SESSION = Annotated[AsyncSession, Depends(get_db)]

async def warm_pool() -> None:
    """Open `POOL_SIZE` connections up front instead of lazily on first use.

    Without this, the pool is empty at boot and the first request per
    connection slot pays for TCP + Postgres auth handshake on top of its own
    query - measured as ~600ms extra on a cold request, both locally and in
    production. Opening and immediately releasing them back to the pool at
    startup means every request after boot gets an already-established
    connection.
    """
    async def open_and_release():
        async with engine.connect():
            pass

    await asyncio.gather(*(open_and_release() for _ in range(POOL_SIZE)))