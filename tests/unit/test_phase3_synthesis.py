import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from osrs_price_forecaster.application.synthesis.service import SynthesisService
from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    ModelEvaluationRecord,
    ModelSelectionRecord,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


class FakeForecastRepository:
    def __init__(self, forecast: ForecastResult | None) -> None:
        self._forecast = forecast

    async def list_forecasts(self, item_id: int, horizon: ForecastHorizon, limit: int = 100) -> list[ForecastResult]:
        if self._forecast is None:
            return []
        return [self._forecast]


class FakeEvaluationRepository:
    def __init__(self, evaluation: ModelEvaluationRecord | None) -> None:
        self._evaluation = evaluation

    async def list_evaluations(self, item_id: int, horizon: ForecastHorizon, limit: int = 100) -> list[ModelEvaluationRecord]:
        if self._evaluation is None:
            return []
        return [self._evaluation]


class FakeSelectionRepository:
    def __init__(self, selection: ModelSelectionRecord | None) -> None:
        self._selection = selection

    async def latest_selection(self, item_id: int, horizon: ForecastHorizon) -> ModelSelectionRecord | None:
        return self._selection


def test_summary_uses_monitor_label_for_healthy_inputs() -> None:
    async def run() -> None:
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

        service = SynthesisService(
            forecast_repository=FakeForecastRepository(forecast),
            evaluation_repository=FakeEvaluationRepository(evaluation),
            selection_repository=FakeSelectionRepository(selection),
        )

        summary = await service.build_summary(item_id=4151, horizon=ForecastHorizon(hours=1))
        assert summary.signal_label == "stable"
        assert summary.liquidity_status == "healthy"
        assert summary.freshness_status == "fresh"

    asyncio.run(run())


def test_signal_returns_avoid_for_stale_and_illiquid_inputs() -> None:
    async def run() -> None:
        now = datetime.now(UTC)
        forecast = ForecastResult(
            item_id=4151,
            horizon=ForecastHorizon(hours=1),
            forecast_created_at=now - timedelta(hours=8),
            forecast_target_at=now + timedelta(hours=1),
            predicted_mid_price=Decimal("1000.0"),
            model_name="naive_last",
            model_version="1.0.0",
            metadata={
                "prediction_interval_low": "500.0",
                "prediction_interval_high": "1500.0",
                "liquidity_filter_min_volume": "10",
                "liquidity_observations_dropped": "6",
                "drift_state": "worsened",
                "drift_ratio": "2.0",
            },
        )
        evaluation = ModelEvaluationRecord(
            id=3,
            item_id=4151,
            horizon=ForecastHorizon(hours=1),
            model_name="naive_last",
            model_version="1.0.0",
            evaluation_window_start=now - timedelta(days=10),
            evaluation_window_end=now,
            metric_mae=Decimal("50.0"),
            metric_rmse=Decimal("60.0"),
            metric_smape=Decimal("0.5"),
            metric_directional_accuracy=Decimal("0.4"),
            metric_bias=Decimal("0.5"),
            created_at=now - timedelta(hours=2),
            fold_count=5,
        )
        selection = ModelSelectionRecord(
            id=4,
            item_id=4151,
            horizon=ForecastHorizon(hours=1),
            selected_model_name="naive_last",
            selected_model_version="1.0.0",
            primary_metric="mae",
            primary_metric_value=Decimal("50.0"),
            reason="Selected by MAE",
            selected_at=now - timedelta(hours=4),
            evaluation_id=3,
        )

        service = SynthesisService(
            forecast_repository=FakeForecastRepository(forecast),
            evaluation_repository=FakeEvaluationRepository(evaluation),
            selection_repository=FakeSelectionRepository(selection),
        )

        signal = await service.build_signal(item_id=4151, horizon=ForecastHorizon(hours=1))
        assert signal.signal_label == "avoid"
        assert "stale_data" in signal.reason_codes
        assert "liquidity_risk" in signal.reason_codes

    asyncio.run(run())
