from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router


class FakeSession:
    pass


class FakeOperationalService:
    def __init__(self, status: dict[str, Any]) -> None:
        self._status = status

    async def build_status(self) -> dict[str, Any]:
        return self._status


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_operational_summary_endpoint_returns_health_and_warnings(monkeypatch: Any) -> None:
    status = {
        "generated_at": datetime.now(UTC),
        "service_status": "ok",
        "freshness_status": "healthy",
        "warnings": ["stale_ingestion"],
        "latest_ingested_at": datetime.now(UTC),
    }

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.OperationalService",
        lambda **kwargs: FakeOperationalService(status),
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    response = client.get("/api/v1/operational-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service_status"] == "ok"
    assert payload["freshness_status"] == "healthy"
    assert payload["warnings"] == ["stale_ingestion"]
