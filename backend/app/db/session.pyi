from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

engine: AsyncEngine
SessionFactory: async_sessionmaker[AsyncSession]

async def get_session() -> AsyncIterator[AsyncSession]: ...
async def get_session_context() -> AsyncIterator[AsyncSession]: ...
async def session_scope() -> AsyncIterator[AsyncSession]: ...
