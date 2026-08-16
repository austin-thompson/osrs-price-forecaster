from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.api.routes.v1 import router
from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    ModelEvaluationRecord,
    ModelSelectionRecord,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


class FakeSession:
    pass


class FakeForecastRepository:
    def __init__(self, forecast: ForecastResult | None) -> None:
        self._forecast = forecast

    async def list_forecasts(
        self, item_id: int, horizon: ForecastHorizon, limit: int = 100
    ) -> list[ForecastResult]:
        if self._forecast is None:
            return []
        return [self._forecast]


class FakeEvaluationRepository:
    def __init__(self, evaluation: ModelEvaluationRecord | None) -> None:
        self._evaluation = evaluation

    async def list_evaluations(
        self, item_id: int, horizon: ForecastHorizon, limit: int = 100
    ) -> list[ModelEvaluationRecord]:
        if self._evaluation is None:
            return []
        return [self._evaluation]


class FakeSelectionRepository:
    def __init__(self, selection: ModelSelectionRecord | None) -> None:
        self._selection = selection

    async def latest_selection(
        self, item_id: int, horizon: ForecastHorizon
    ) -> ModelSelectionRecord | None:
        return self._selection


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_phase3_summary_endpoint_returns_synthesis_payload(monkeypatch: Any) -> None:
    now = datetime.now(UTC)
    forecast = ForecastResult(
        item_id=4151,
        horizon=ForecastHorizon(hours=1),
        forecast_created_at=now - timedelta(minutes=20),
        forecast_target_at=now + timedelta(hours=1),
        predicted_mid_price=Decimal("1000.0"),
        model_name="naive_last",
        model_version="1.0.0",
        metadata={
            "prediction_interval_low": "900.0",
            "prediction_interval_high": "1100.0",
            "liquidity_filter_min_volume": "10",
            "liquidity_observations_dropped": "1",
            "drift_state": "stable",
            "drift_ratio": "1.0",
        },
    )
    evaluation = ModelEvaluationRecord(
        id=1,
        item_id=4151,
        horizon=ForecastHorizon(hours=1),
        model_name="naive_last",
        model_version="1.0.0",
        evaluation_window_start=now - timedelta(days=10),
        evaluation_window_end=now,
        metric_mae=Decimal("10.0"),
        metric_rmse=Decimal("12.0"),
        metric_smape=Decimal("0.1"),
        metric_directional_accuracy=Decimal("0.6"),
        metric_bias=Decimal("0.2"),
        created_at=now - timedelta(hours=1),
        fold_count=20,
    )
    selection = ModelSelectionRecord(
        id=2,
        item_id=4151,
        horizon=ForecastHorizon(hours=1),
        selected_model_name="naive_last",
        selected_model_version="1.0.0",
        primary_metric="mae",
        primary_metric_value=Decimal("10.0"),
        reason="Selected by MAE",
        selected_at=now - timedelta(minutes=10),
        evaluation_id=1,
    )

    async def fake_synthesis_service_factory(*args: object, **kwargs: object) -> Any:
        return Any

    monkeypatch.setattr(
        "osrs_price_forecaster.api.routes.v1.SynthesisService",
        lambda **kwargs: FakeSynthesisService(forecast, evaluation, selection),
    )

    class FakeSynthesisService:
        def __init__(
            self,
            forecast: ForecastResult,
            evaluation: ModelEvaluationRecord,
            selection: ModelSelectionRecord,
        ) -> None:
            self._forecast = forecast
            self._evaluation = evaluation
            self._selection = selection

        async def build_summary(self, *, item_id: int, horizon: ForecastHorizon) -> Any:
            return type(
                "Summary",
                (),
                {
                    "item_id": item_id,
                    "horizon_hours": horizon.hours,
                    "generated_at": now,
                    "champion_model_name": self._selection.selected_model_name,
                    "champion_model_version": self._selection.selected_model_version,
                    "predicted_mid_price": self._forecast.predicted_mid_price,
                    "prediction_interval_low": Decimal("900.0"),
                    "prediction_interval_high": Decimal("1100.0"),
                    "drift_state": "stable",
                    "drift_ratio": Decimal("1.0"),
                    "liquidity_status": "healthy",
                    "freshness_status": "fresh",
                    "signal_label": "stable",
                    "score": Decimal("0.85"),
                    "reason_codes": ["stable_drift"],
                },
            )()

        async def build_signal(self, *, item_id: int, horizon: ForecastHorizon) -> Any:
            return type(
                "Signal",
                (),
                {
                    "item_id": item_id,
                    "horizon_hours": horizon.hours,
                    "signal_label": "stable",
                    "score": Decimal("0.85"),
                    "reason_codes": ["stable_drift"],
                    "guardrail_status": "pass",
                },
            )()

        async def build_explanation(self, *, item_id: int, horizon: ForecastHorizon) -> Any:
            return type(
                "Explanation",
                (),
                {
                    "item_id": item_id,
                    "horizon_hours": horizon.hours,
                    "champion_model_name": self._selection.selected_model_name,
                    "champion_model_version": self._selection.selected_model_version,
                    "metric_mae": Decimal("10.0"),
                    "metric_directional_accuracy": Decimal("0.6"),
                    "liquidity_observations_dropped": 1,
                    "drift_ratio": Decimal("1.0"),
                    "interval_width": Decimal("200.0"),
                    "freshness_minutes": 20,
                    "reason_codes": ["stable_drift"],
                },
            )()

    app = _build_test_app()
    app.dependency_overrides[get_db_session] = lambda: iter([FakeSession()])
    client = TestClient(app)
    response = client.get("/api/v1/items/4151/summary?horizon_hours=1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal_label"] == "stable"
    assert payload["liquidity_status"] == "healthy"
    assert payload["reason_codes"] == ["stable_drift"]
