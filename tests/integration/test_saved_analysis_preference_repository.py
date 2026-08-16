from uuid import uuid4

import pytest

from osrs_price_forecaster.domain.value_objects import ForecastHorizon
from osrs_price_forecaster.infrastructure.database.repositories import (
    SqlAlchemySavedAnalysisPreferenceRepository,
    SqlAlchemySavedWatchlistRepository,
)
from osrs_price_forecaster.infrastructure.database.session import async_session_factory


@pytest.mark.integration
async def test_saved_analysis_preference_repository_round_trip_and_watchlist_nulling() -> None:
    async with async_session_factory() as session:
        preferences = SqlAlchemySavedAnalysisPreferenceRepository(session)
        watchlists = SqlAlchemySavedWatchlistRepository(session)
        watchlist = await watchlists.create_watchlist(
            name=f"integration-{uuid4()}", item_ids=[4151, 11840]
        )
        preference = await preferences.create_preference(
            name=f"integration-{uuid4()}",
            horizon=ForecastHorizon(hours=6),
            signal_labels=["stable", "caution"],
            liquidity_statuses=["healthy"],
            drift_states=["stable", "improved"],
            top_n=25,
            watchlist_id=watchlist.id,
        )

        try:
            assert await preferences.get_preference(preference.id) == preference
            assert preference in await preferences.list_preferences()

            assert await watchlists.delete_watchlist(watchlist.id) is True
            fetched = await preferences.get_preference(preference.id)
            assert fetched is not None
            assert fetched.watchlist_id is None

            assert await preferences.delete_preference(preference.id) is True
            assert await preferences.get_preference(preference.id) is None
        finally:
            if await preferences.get_preference(preference.id) is not None:
                await preferences.delete_preference(preference.id)
            if await watchlists.get_watchlist(watchlist.id) is not None:
                await watchlists.delete_watchlist(watchlist.id)
