from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router
from osrs_price_forecaster.domain.entities import SavedAnalysisPreference, Watchlist
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


class FakeSession:
    pass


class FakePreferenceRepository:
    def __init__(self) -> None:
        self._preferences: list[SavedAnalysisPreference] = []

    async def list_preferences(self) -> list[SavedAnalysisPreference]:
        return list(reversed(self._preferences))

    async def create_preference(
        self,
        *,
        name: str,
        horizon: ForecastHorizon,
        signal_labels: list[str],
        liquidity_statuses: list[str],
        drift_states: list[str],
        top_n: int,
        watchlist_id: int | None,
    ) -> SavedAnalysisPreference:
        preference = SavedAnalysisPreference(
            id=len(self._preferences) + 1,
            name=name,
            horizon=horizon,
            signal_labels=signal_labels,
            liquidity_statuses=liquidity_statuses,
            drift_states=drift_states,
            top_n=top_n,
            watchlist_id=watchlist_id,
            created_at=datetime.now(UTC),
        )
        self._preferences.append(preference)
        return preference

    async def get_preference(self, preference_id: int) -> SavedAnalysisPreference | None:
        return next(
            (preference for preference in self._preferences if preference.id == preference_id),
            None,
        )

    async def delete_preference(self, preference_id: int) -> bool:
        preference = await self.get_preference(preference_id)
        if preference is None:
            return False
        self._preferences.remove(preference)
        return True


class FakeWatchlistRepository:
    def __init__(self, watchlists: list[Watchlist] | None = None) -> None:
        self._watchlists = watchlists or []

    async def get_watchlist(self, watchlist_id: int) -> Watchlist | None:
        return next(
            (watchlist for watchlist in self._watchlists if watchlist.id == watchlist_id),
            None,
        )


def _build_client(monkeypatch: Any, *, with_watchlist: bool = True) -> TestClient:
    preferences = FakePreferenceRepository()
    watchlists = [Watchlist(id=7, name="Tracked", item_ids=[4151, 11840])] if with_watchlist else []
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SqlAlchemySavedAnalysisPreferenceRepository",
        lambda session: preferences,
    )
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SqlAlchemySavedWatchlistRepository",
        lambda session: FakeWatchlistRepository(watchlists),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    return TestClient(app)


def _valid_payload() -> dict[str, object]:
    return {
        "name": "  Stable shortlist  ",
        "horizon_hours": 6,
        "signal_labels": ["stable", "caution"],
        "liquidity_statuses": ["healthy"],
        "drift_states": ["stable", "improved"],
        "top_n": 25,
        "watchlist_id": 7,
    }


def test_saved_preference_crud_endpoints(monkeypatch: Any) -> None:
    client = _build_client(monkeypatch)

    created_response = client.post("/api/v1/preferences", json=_valid_payload())
    assert created_response.status_code == 200
    created = created_response.json()
    assert created["name"] == "Stable shortlist"
    assert created["horizon_hours"] == 6
    assert created["watchlist_id"] == 7

    listed_response = client.get("/api/v1/preferences")
    assert listed_response.status_code == 200
    assert listed_response.json() == [created]

    fetched_response = client.get(f"/api/v1/preferences/{created['id']}")
    assert fetched_response.status_code == 200
    assert fetched_response.json() == created

    deleted_response = client.delete(f"/api/v1/preferences/{created['id']}")
    assert deleted_response.status_code == 204
    assert client.get(f"/api/v1/preferences/{created['id']}").status_code == 404


def test_saved_preference_rejects_invalid_filters_and_horizon(monkeypatch: Any) -> None:
    client = _build_client(monkeypatch)
    duplicate_payload = _valid_payload()
    duplicate_payload["signal_labels"] = ["stable", "stable"]
    assert client.post("/api/v1/preferences", json=duplicate_payload).status_code == 422

    unsupported_payload = _valid_payload()
    unsupported_payload["drift_states"] = ["volatile"]
    assert client.post("/api/v1/preferences", json=unsupported_payload).status_code == 422

    horizon_payload = _valid_payload()
    horizon_payload["horizon_hours"] = 2
    response = client.post("/api/v1/preferences", json=horizon_payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "horizon_hours must be one of [1, 6, 24]"


def test_saved_preference_requires_existing_watchlist(monkeypatch: Any) -> None:
    client = _build_client(monkeypatch, with_watchlist=False)
    response = client.post("/api/v1/preferences", json=_valid_payload())
    assert response.status_code == 404
    assert response.json()["detail"] == "watchlist not found"
