from uuid import uuid4

import pytest

from osrs_price_forecaster.infrastructure.database.repositories import (
    SqlAlchemySavedWatchlistRepository,
)
from osrs_price_forecaster.infrastructure.database.session import async_session_factory


@pytest.mark.integration
async def test_watchlist_repository_crud_round_trip() -> None:
    async with async_session_factory() as session:
        repository = SqlAlchemySavedWatchlistRepository(session)
        name = f"integration-{uuid4()}"
        created = await repository.create_watchlist(name=name, item_ids=[4151, 11840])

        try:
            fetched = await repository.get_watchlist(created.id)
            assert fetched == created

            listed = await repository.list_watchlists()
            assert created in listed

            assert await repository.delete_watchlist(created.id) is True
            assert await repository.get_watchlist(created.id) is None
        finally:
            if await repository.get_watchlist(created.id) is not None:
                await repository.delete_watchlist(created.id)
