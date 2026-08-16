from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import OperationalService, router


class FakeSession:
    pass


class FakeOperationalService:
    def __init__(self, status: dict[str, Any]) -> None:
        self._status = status

    async def build_status(self) -> dict[str, Any]:
        return self._status


class FakeResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class FakeQuery:
    def order_by(self, *args: Any) -> "FakeQuery":
        return self

    def limit(self, value: int) -> "FakeQuery":
        return self


class FakeSessionWithLatestObservation:
    def __init__(self, latest_ingested_at: datetime | None) -> None:
        self._latest_ingested_at = latest_ingested_at

    async def execute(self, stmt: Any) -> FakeResult:
        return FakeResult(self._latest_ingested_at)


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


async def test_operational_service_uses_latest_observation_freshness(monkeypatch: Any) -> None:
    latest_ingested_at = datetime.now(UTC) - timedelta(minutes=200)
    fake_session = FakeSessionWithLatestObservation(latest_ingested_at)

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.select",
        lambda *args, **kwargs: FakeQuery(),
    )
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.desc",
        lambda *args, **kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.PriceObservationModel",
        type("PriceObservationModel", (), {"ingested_at": object()}),
    )

    service = OperationalService(session=cast(AsyncSession, fake_session))
    status = await service.build_status()
    assert status.freshness_status == "stale"
    assert status.service_status == "degraded"
    assert "stale_ingestion" in status.warnings
