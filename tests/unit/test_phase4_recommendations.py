from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router


class FakeSession:
    pass


class FakeRecommendationService:
    def __init__(self, recommendations: list[dict[str, Any]]) -> None:
        self._recommendations = recommendations

    async def list_recommendations(self, *, horizon_hours: int, limit: int = 100) -> list[dict[str, Any]]:
        return self._recommendations


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_recommendations_endpoint_returns_ranked_items(monkeypatch: Any) -> None:
    recommendations = [
        {
            "item_id": 4151,
            "horizon_hours": 1,
            "signal_label": "stable",
            "score": Decimal("0.85"),
            "reason_codes": ["stable_drift"],
            "guardrail_status": "pass",
            "champion_model_name": "naive_last",
            "champion_model_version": "1.0.0",
        },
        {
            "item_id": 11840,
            "horizon_hours": 1,
            "signal_label": "caution",
            "score": Decimal("0.55"),
            "reason_codes": ["wide_interval"],
            "guardrail_status": "warn",
            "champion_model_name": "ewma_0.4",
            "champion_model_version": "1.0.0",
        },
    ]

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.RecommendationService",
        lambda **kwargs: FakeRecommendationService(recommendations),
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    response = client.get("/api/v1/recommendations?horizon_hours=1")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["item_id"] == 4151
    assert payload[0]["signal_label"] == "stable"
    assert payload[1]["signal_label"] == "caution"
