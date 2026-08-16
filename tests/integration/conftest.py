from collections.abc import AsyncIterator

import pytest_asyncio

from osrs_price_forecaster.infrastructure.database.session import engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_engine_after_test() -> AsyncIterator[None]:
    yield
    await engine.dispose()
