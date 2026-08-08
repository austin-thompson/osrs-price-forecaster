from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from osrs_price_forecaster.application.forecasting.service import ForecastingService
from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    ModelEvaluationRecord,
    ModelSelectionRecord,
    PriceObservation,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon
from osrs_price_forecaster.infrastructure.forecasting.baseline_models import (
    NaiveLastValueModel,
    RollingMeanModel,
)
from osrs_price_forecaster.infrastructure.forecasting.registry import InMemoryCandidateModelRegistry


class FakePriceObservationRepository:
    def __init__(self, observations: list[PriceObservation]) -> None:
        self._observations = observations

    async def store_observations(self, observations: Sequence[PriceObservation]) -> int:
        self._observations.extend(observations)
        return len(observations)

    async def list_observations(
        self,
        item_id: int,
        interval: str,
        start_at: datetime | None,
        end_at: datetime | None,
        limit: int = 500,
    ) -> list[PriceObservation]:
        _ = (start_at, end_at)
        result = [
            obs for obs in self._observations if obs.item_id == item_id and obs.interval == interval
        ]
        return result[:limit]


class FakeForecastRepository:
    def __init__(self) -> None:
        self.forecasts: list[ForecastResult] = []

    async def store_forecast(self, forecast: ForecastResult) -> int:
        self.forecasts.append(forecast)
        return 1

    async def list_forecasts(
        self,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ForecastResult]:
        result = [f for f in self.forecasts if f.item_id == item_id and f.horizon == horizon]
        return result[:limit]


class FakeModelEvaluationRepository:
    def __init__(self) -> None:
        self.records: list[ModelEvaluationRecord] = []

    async def store_evaluation(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        model_name: str,
        model_version: str,
        evaluation_window_start: datetime,
        evaluation_window_end: datetime,
        metric_mae: Decimal | None,
        metric_rmse: Decimal | None,
        metric_smape: Decimal | None,
        metric_directional_accuracy: Decimal | None,
        metric_bias: Decimal | None,
        created_at: datetime,
        metadata: dict[str, str],
    ) -> ModelEvaluationRecord:
        record = ModelEvaluationRecord(
            id=len(self.records) + 1,
            item_id=item_id,
            horizon=horizon,
            model_name=model_name,
            model_version=model_version,
            evaluation_window_start=evaluation_window_start,
            evaluation_window_end=evaluation_window_end,
            metric_mae=metric_mae,
            metric_rmse=metric_rmse,
            metric_smape=metric_smape,
            metric_directional_accuracy=metric_directional_accuracy,
            metric_bias=metric_bias,
            created_at=created_at,
            fold_count=int(metadata.get("fold_count", "0")),
        )
        self.records.append(record)
        return record

    async def list_evaluations(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ModelEvaluationRecord]:
        result = [
            r for r in self.records if r.item_id == item_id and r.horizon.hours == horizon.hours
        ]
        return result[:limit]


class FakeModelSelectionRepository:
    def __init__(self) -> None:
        self.records: list[ModelSelectionRecord] = []

    async def store_selection(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        selected_model_name: str,
        selected_model_version: str,
        primary_metric: str,
        primary_metric_value: Decimal | None,
        reason: str,
        selected_at: datetime,
        evaluation_id: int | None,
    ) -> ModelSelectionRecord:
        record = ModelSelectionRecord(
            id=len(self.records) + 1,
            item_id=item_id,
            horizon=horizon,
            selected_model_name=selected_model_name,
            selected_model_version=selected_model_version,
            primary_metric=primary_metric,
            primary_metric_value=primary_metric_value,
            reason=reason,
            selected_at=selected_at,
            evaluation_id=evaluation_id,
        )
        self.records.append(record)
        return record

    async def latest_selection(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ModelSelectionRecord | None:
        result = [
            r for r in self.records if r.item_id == item_id and r.horizon.hours == horizon.hours
        ]
        return result[-1] if result else None


def _build_hourly_observations() -> list[PriceObservation]:
    start = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    observations: list[PriceObservation] = []
    for idx in range(36):
        high = 2_000_000 + (idx * 1_000)
        low = 1_990_000 + (idx * 1_000)
        mid = (Decimal(high) + Decimal(low)) / Decimal(2)
        ts = start + timedelta(hours=idx)
        observations.append(
            PriceObservation(
                item_id=4151,
                interval="1h",
                source_timestamp=ts,
                ingested_at=ts,
                avg_high_price=high,
                avg_low_price=low,
                high_price_volume=50,
                low_price_volume=48,
                mid_price=mid,
            )
        )
    return observations


@pytest.mark.asyncio
async def test_forecasting_service_persists_evaluations_selection_and_forecast() -> None:
    price_repo = FakePriceObservationRepository(_build_hourly_observations())
    forecast_repo = FakeForecastRepository()
    evaluation_repo = FakeModelEvaluationRepository()
    selection_repo = FakeModelSelectionRepository()

    service = ForecastingService(
        registry=InMemoryCandidateModelRegistry(
            _models=[NaiveLastValueModel(), RollingMeanModel(window_size=3)]
        ),
        price_repository=price_repo,
        forecast_repository=forecast_repo,
        evaluation_repository=evaluation_repo,
        selection_repository=selection_repo,
        tracked_item_ids=[4151],
        forecast_horizons_hours=[1],
        minimum_training_observations=24,
    )

    await service.run_once()

    assert len(evaluation_repo.records) >= 1
    assert len(selection_repo.records) == 1
    assert len(forecast_repo.forecasts) == 1
    assert forecast_repo.forecasts[0].horizon.hours == 1
    assert "prediction_interval_low" in forecast_repo.forecasts[0].metadata
    assert "prediction_interval_high" in forecast_repo.forecasts[0].metadata
    assert "drift_state" in forecast_repo.forecasts[0].metadata


@pytest.mark.asyncio
async def test_forecasting_service_skips_low_liquidity_observations() -> None:
    low_liquidity = _build_hourly_observations()
    low_liquidity = [
        PriceObservation(
            item_id=obs.item_id,
            interval=obs.interval,
            source_timestamp=obs.source_timestamp,
            ingested_at=obs.ingested_at,
            avg_high_price=obs.avg_high_price,
            avg_low_price=obs.avg_low_price,
            high_price_volume=1,
            low_price_volume=1,
            mid_price=obs.mid_price,
        )
        for obs in low_liquidity
    ]

    price_repo = FakePriceObservationRepository(low_liquidity)
    forecast_repo = FakeForecastRepository()
    evaluation_repo = FakeModelEvaluationRepository()
    selection_repo = FakeModelSelectionRepository()

    service = ForecastingService(
        registry=InMemoryCandidateModelRegistry(
            _models=[NaiveLastValueModel(), RollingMeanModel(window_size=3)]
        ),
        price_repository=price_repo,
        forecast_repository=forecast_repo,
        evaluation_repository=evaluation_repo,
        selection_repository=selection_repo,
        tracked_item_ids=[4151],
        forecast_horizons_hours=[1],
        minimum_training_observations=24,
        minimum_liquidity_volume=10,
    )

    await service.run_once()

    assert len(evaluation_repo.records) == 0
    assert len(selection_repo.records) == 0
    assert len(forecast_repo.forecasts) == 0
