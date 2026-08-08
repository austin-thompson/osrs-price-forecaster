from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router
from osrs_price_forecaster.domain.entities import Watchlist


class FakeSession:
    pass


class FakeWatchlistRepository:
    def __init__(self) -> None:
        self._watchlists: list[Watchlist] = []

    async def list_watchlists(self) -> list[Watchlist]:
        return list(self._watchlists)

    async def create_watchlist(self, *, name: str, item_ids: list[int]) -> Watchlist:
        watchlist = Watchlist(id=len(self._watchlists) + 1, name=name, item_ids=list(item_ids))
        self._watchlists.append(watchlist)
        return watchlist

    async def get_watchlist(self, watchlist_id: int) -> Watchlist | None:
        for watchlist in self._watchlists:
            if watchlist.id == watchlist_id:
                return watchlist
        return None

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        for index, watchlist in enumerate(self._watchlists):
            if watchlist.id == watchlist_id:
                del self._watchlists[index]
                return True
        return False


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_watchlist_endpoints_persist_and_list_saved_items(monkeypatch: Any) -> None:
    repository = FakeWatchlistRepository()
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SqlAlchemySavedWatchlistRepository",
        lambda session: repository,
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/watchlists",
        json={"name": "focus-list", "item_ids": [4151, 11840]},
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["name"] == "focus-list"
    assert payload["item_ids"] == [4151, 11840]

    list_response = client.get("/api/v1/watchlists")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "focus-list"
    assert list_response.json()[0]["item_ids"] == [4151, 11840]


def test_watchlist_get_and_delete_endpoints(monkeypatch: Any) -> None:
    repository = FakeWatchlistRepository()
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SqlAlchemySavedWatchlistRepository",
        lambda session: repository,
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/watchlists",
        json={"name": "focus-list", "item_ids": [4151, 11840]},
    )
    watchlist_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == watchlist_id

    delete_response = client.delete(f"/api/v1/watchlists/{watchlist_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert missing_response.status_code == 404
