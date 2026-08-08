from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.health import router


class HealthySession:
    async def execute(self, _query: object) -> int:
        return 1


class UnhealthySession:
    async def execute(self, _query: object) -> int:
        raise RuntimeError("db down")


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


async def _healthy_dep() -> AsyncIterator[HealthySession]:
    yield HealthySession()


async def _unhealthy_dep() -> AsyncIterator[UnhealthySession]:
    yield UnhealthySession()


def test_live_endpoint() -> None:
    client = TestClient(_build_test_app())
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint_ok() -> None:
    app = _build_test_app()
    app.dependency_overrides[get_db_session] = _healthy_dep
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint_degraded() -> None:
    app = _build_test_app()
    app.dependency_overrides[get_db_session] = _unhealthy_dep
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
