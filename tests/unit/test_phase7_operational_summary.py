from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
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
        "warning_details": [
            {
                "code": "stale_ingestion",
                "category": "ingestion_freshness",
                "severity": "error",
                "message": "The latest price ingestion is stale.",
            }
        ],
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
    assert payload["warning_details"][0]["category"] == "ingestion_freshness"
    assert payload["warning_details"][0]["severity"] == "error"


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
    assert status.warning_details[0].category == "ingestion_freshness"
    assert status.warning_details[0].severity == "error"


async def test_operational_service_uses_configured_freshness_thresholds(
    monkeypatch: Any,
) -> None:
    latest_ingested_at = datetime.now(UTC) - timedelta(minutes=50)
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

    service = OperationalService(
        session=cast(AsyncSession, fake_session),
        freshness_warning_minutes=15,
        freshness_stale_minutes=45,
    )
    status = await service.build_status()

    assert status.freshness_status == "stale"
    assert status.warnings == ["stale_ingestion"]


@pytest.mark.parametrize(
    ("age_minutes", "expected_freshness", "expected_code", "expected_severity"),
    [
        (89, "healthy", None, None),
        (90, "warning", "ingestion_delay", "warning"),
        (179, "warning", "ingestion_delay", "warning"),
        (180, "stale", "stale_ingestion", "error"),
    ],
)
async def test_operational_freshness_boundaries_are_stable(
    monkeypatch: Any,
    age_minutes: int,
    expected_freshness: str,
    expected_code: str | None,
    expected_severity: str | None,
) -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    fake_session = FakeSessionWithLatestObservation(now - timedelta(minutes=age_minutes))
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

    status = await OperationalService(
        session=cast(AsyncSession, fake_session), now_provider=lambda: now
    ).build_status()

    assert status.freshness_status == expected_freshness
    assert status.service_status == ("ok" if expected_code is None else "degraded")
    assert status.warnings == ([] if expected_code is None else [expected_code])
    assert [warning.severity for warning in status.warning_details] == (
        [] if expected_severity is None else [expected_severity]
    )


async def test_operational_missing_data_has_availability_classification(
    monkeypatch: Any,
) -> None:
    fake_session = FakeSessionWithLatestObservation(None)
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

    status = await OperationalService(session=cast(AsyncSession, fake_session)).build_status()

    assert status.warnings == ["no_price_observations"]
    assert status.warning_details[0].category == "data_availability"
    assert status.warning_details[0].severity == "error"
