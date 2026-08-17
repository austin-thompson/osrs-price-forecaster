from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router


class FakeSession:
    pass


class FakeSynthesisService:
    def __init__(
        self, summary: dict[str, Any], signal: dict[str, Any], explanation: dict[str, Any]
    ) -> None:
        self._summary = summary
        self._signal = signal
        self._explanation = explanation

    async def build_summary(self, *, item_id: int, horizon: Any) -> dict[str, Any]:
        return self._summary

    async def build_signal(self, *, item_id: int, horizon: Any) -> dict[str, Any]:
        return self._signal

    async def build_explanation(self, *, item_id: int, horizon: Any) -> dict[str, Any]:
        return self._explanation


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_analysis_summary_endpoint_returns_combined_insights(monkeypatch: Any) -> None:
    summary = {
        "item_id": 4151,
        "horizon_hours": 1,
        "signal_label": "stable",
        "score": Decimal("0.85"),
        "reason_codes": ["stable_drift"],
        "guardrail_status": "pass",
        "champion_model_name": "naive_last",
        "champion_model_version": "1.0.0",
        "liquidity_status": "healthy",
        "freshness_status": "fresh",
    }
    signal = {
        "item_id": 4151,
        "horizon_hours": 1,
        "signal_label": "stable",
        "score": Decimal("0.85"),
        "reason_codes": ["stable_drift"],
        "guardrail_status": "pass",
    }
    explanation = {
        "item_id": 4151,
        "horizon_hours": 1,
        "champion_model_name": "naive_last",
        "champion_model_version": "1.0.0",
        "metric_mae": Decimal("12.5"),
        "metric_directional_accuracy": Decimal("0.75"),
        "liquidity_observations_dropped": 1,
        "drift_ratio": Decimal("0.1"),
        "interval_width": Decimal("25"),
        "freshness_minutes": 45,
        "drift_state": "stable",
        "liquidity_status": "healthy",
        "freshness_status": "fresh",
        "reason_codes": ["stable_drift"],
        "evidence_summary": ["Recent model drift is stable."],
    }

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SynthesisService",
        lambda **kwargs: FakeSynthesisService(summary, signal, explanation),
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    response = client.get("/api/v1/items/4151/analysis-summary?horizon_hours=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["item_id"] == 4151
    assert payload["signal_label"] == "stable"
    assert payload["champion_model_name"] == "naive_last"
    assert payload["liquidity_status"] == "healthy"
    assert payload["freshness_status"] == "fresh"
    assert payload["reason_codes"] == ["stable_drift"]


def test_cohort_comparison_endpoint_returns_side_by_side_signals(monkeypatch: Any) -> None:
    summary = {
        "item_id": 4151,
        "horizon_hours": 1,
        "signal_label": "stable",
        "score": Decimal("0.85"),
        "reason_codes": ["stable_drift"],
        "guardrail_status": "pass",
        "champion_model_name": "naive_last",
        "champion_model_version": "1.0.0",
        "liquidity_status": "healthy",
        "freshness_status": "fresh",
    }
    signal = {
        "item_id": 4151,
        "horizon_hours": 1,
        "signal_label": "stable",
        "score": Decimal("0.85"),
        "reason_codes": ["stable_drift"],
        "guardrail_status": "pass",
    }
    explanation = {
        "item_id": 4151,
        "horizon_hours": 1,
        "champion_model_name": "naive_last",
        "champion_model_version": "1.0.0",
        "metric_mae": Decimal("12.5"),
        "metric_directional_accuracy": Decimal("0.75"),
        "liquidity_observations_dropped": 1,
        "drift_ratio": Decimal("0.1"),
        "interval_width": Decimal("25"),
        "freshness_minutes": 45,
        "drift_state": "stable",
        "liquidity_status": "healthy",
        "freshness_status": "fresh",
        "reason_codes": ["stable_drift"],
        "evidence_summary": ["Recent model drift is stable."],
    }

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SynthesisService",
        lambda **kwargs: FakeSynthesisService(summary, signal, explanation),
    )

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)

    response = client.get("/api/v1/cohort-comparison?item_ids=4151&item_ids=11840&horizon_hours=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["horizon_hours"] == 1
    assert len(payload["items"]) == 2
    assert payload["items"][0]["item_id"] == 4151
    assert payload["items"][0]["signal_label"] == "stable"
    assert payload["items"][0]["drift_state"] == "stable"
    assert payload["items"][0]["drift_ratio"] == "0.1"
    assert payload["items"][0]["interval_width"] == "25"
    assert payload["items"][0]["freshness_minutes"] == 45
    assert payload["items"][0]["primary_reason_code"] == "stable_drift"
    assert payload["items"][0]["comparison_summary"] == (
        "Signal is stable; primary reason is stable_drift; freshness is fresh, "
        "liquidity is healthy, and drift is stable."
    )
