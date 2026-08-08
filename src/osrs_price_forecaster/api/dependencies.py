from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from osrs_price_forecaster.infrastructure.database.session import async_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
