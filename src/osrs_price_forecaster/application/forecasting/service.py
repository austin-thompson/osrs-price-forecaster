from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from math import sqrt

from osrs_price_forecaster.domain.entities import (
    ForecastRequest,
    ForecastResult,
    ModelEvaluationRecord,
    PriceObservation,
)
from osrs_price_forecaster.domain.forecasting import (
    CandidateModelRegistry,
    ForecastModel,
)
from osrs_price_forecaster.domain.repositories import (
    ForecastRepository,
    ModelEvaluationRepository,
    ModelSelectionRepository,
    PriceObservationRepository,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


@dataclass(slots=True)
class ForecastingService:
    """Phase 2 forecasting orchestrator with uncertainty and drift signals."""

    registry: CandidateModelRegistry
    price_repository: PriceObservationRepository
    forecast_repository: ForecastRepository
    evaluation_repository: ModelEvaluationRepository
    selection_repository: ModelSelectionRepository
    tracked_item_ids: list[int]
    forecast_horizons_hours: list[int]
    minimum_training_observations: int = 24
    minimum_liquidity_volume: int = 1
    prediction_interval_confidence: Decimal = Decimal("0.80")
    drift_alert_ratio: Decimal = Decimal("1.25")

    async def run_once(self) -> None:
        for item_id in self.tracked_item_ids:
            observations = await self.price_repository.list_observations(
                item_id=item_id,
                interval="1h",
                start_at=None,
                end_at=None,
                limit=2_000,
            )
            ordered = list(reversed([obs for obs in observations if obs.mid_price is not None]))
            filtered, dropped_liquidity = _apply_liquidity_filter(
                ordered,
                minimum_liquidity_volume=self.minimum_liquidity_volume,
            )

            for horizon_hours in self.forecast_horizons_hours:
                horizon = ForecastHorizon(hours=horizon_hours)
                bundles = await self._evaluate_models_for_horizon(
                    item_id=item_id,
                    horizon=horizon,
                    observations=filtered,
                    dropped_liquidity=dropped_liquidity,
                )
                if not bundles:
                    continue

                evaluations = [bundle.evaluation for bundle in bundles]

                selected = min(
                    evaluations,
                    key=lambda record: (
                        record.metric_mae if record.metric_mae is not None else Decimal("1e18")
                    ),
                )

                selected_bundle = next(
                    (bundle for bundle in bundles if bundle.evaluation.id == selected.id),
                    None,
                )
                if selected_bundle is None:
                    continue

                drift_ratio, drift_state = await self._compute_drift_state(
                    item_id=item_id,
                    horizon=horizon,
                    model_name=selected.model_name,
                    model_version=selected.model_version,
                )
                await self.selection_repository.store_selection(
                    item_id=item_id,
                    horizon=horizon,
                    selected_model_name=selected.model_name,
                    selected_model_version=selected.model_version,
                    primary_metric="mae",
                    primary_metric_value=selected.metric_mae,
                    reason=(
                        "Selected by minimum MAE from walk-forward evaluation "
                        f"over {selected.fold_count} folds. "
                        f"Drift signal: {drift_state}"
                        + (f" (ratio={drift_ratio})." if drift_ratio is not None else ".")
                    ),
                    selected_at=datetime.now(UTC),
                    evaluation_id=selected.id,
                )

                model = self._resolve_model(
                    selected.model_name,
                    selected.model_version,
                )
                if model is None:
                    continue

                await model.train(filtered)
                created_at = datetime.now(UTC)
                request = ForecastRequest(
                    item_id=item_id,
                    horizon=horizon,
                    forecast_created_at=created_at,
                )
                forecast = await model.forecast(request)
                low_bound, high_bound = _prediction_interval_bounds(
                    base_value=forecast.predicted_mid_price,
                    residuals=selected_bundle.residuals,
                    confidence=self.prediction_interval_confidence,
                )
                metadata = dict(forecast.metadata)
                metadata.update(
                    {
                        "prediction_interval_confidence": str(self.prediction_interval_confidence),
                        "prediction_interval_low": str(low_bound),
                        "prediction_interval_high": str(high_bound),
                        "liquidity_filter_min_volume": str(self.minimum_liquidity_volume),
                        "liquidity_observations_dropped": str(dropped_liquidity),
                        "drift_state": drift_state,
                    }
                )
                if drift_ratio is not None:
                    metadata["drift_ratio"] = str(drift_ratio)
                forecast = _with_forecast_metadata(forecast, metadata)
                await self.forecast_repository.store_forecast(forecast)

    def _resolve_model(self, name: str, version: str) -> ForecastModel | None:
        for model in self.registry.list_candidates():
            if model.name == name and model.version == version:
                return model
        return None

    async def _evaluate_models_for_horizon(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        observations: list[PriceObservation],
        dropped_liquidity: int,
    ) -> list["ModelEvaluationBundle"]:
        step = horizon.hours
        if len(observations) < self.minimum_training_observations + step:
            return []

        results: list[ModelEvaluationBundle] = []
        for model in self.registry.list_candidates():
            fold_errors: list[Decimal] = []
            fold_targets: list[Decimal] = []
            fold_predictions: list[Decimal] = []

            for end_idx in range(self.minimum_training_observations, len(observations)):
                target_idx = (end_idx - 1) + step
                if target_idx >= len(observations):
                    break

                training_slice = observations[:end_idx]
                await model.train(training_slice)
                created_at = training_slice[-1].source_timestamp
                request = ForecastRequest(
                    item_id=item_id,
                    horizon=horizon,
                    forecast_created_at=created_at,
                )
                predicted = await model.forecast(request)
                actual = observations[target_idx].mid_price
                if actual is None:
                    continue

                fold_predictions.append(predicted.predicted_mid_price)
                fold_targets.append(actual)
                fold_errors.append(predicted.predicted_mid_price - actual)

            if not fold_errors:
                continue

            metrics = _compute_metrics(fold_errors, fold_predictions, fold_targets)
            evaluation = await self.evaluation_repository.store_evaluation(
                item_id=item_id,
                horizon=horizon,
                model_name=model.name,
                model_version=model.version,
                evaluation_window_start=observations[
                    self.minimum_training_observations - 1
                ].source_timestamp,
                evaluation_window_end=observations[-1].source_timestamp,
                metric_mae=metrics.mae,
                metric_rmse=metrics.rmse,
                metric_smape=metrics.smape,
                metric_directional_accuracy=metrics.directional_accuracy,
                metric_bias=metrics.bias,
                created_at=datetime.now(UTC),
                metadata={
                    "fold_count": str(len(fold_errors)),
                    "liquidity_observations_dropped": str(dropped_liquidity),
                    "prediction_interval_confidence": str(self.prediction_interval_confidence),
                },
            )
            results.append(ModelEvaluationBundle(evaluation=evaluation, residuals=fold_errors))

        return results

    async def _compute_drift_state(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        model_name: str,
        model_version: str,
    ) -> tuple[Decimal | None, str]:
        evaluations = await self.evaluation_repository.list_evaluations(
            item_id=item_id,
            horizon=horizon,
            limit=100,
        )
        same_model = [
            record
            for record in evaluations
            if record.model_name == model_name and record.model_version == model_version
        ]
        if len(same_model) < 2:
            return None, "insufficient_history"

        current_mae = same_model[0].metric_mae
        previous_mae = same_model[1].metric_mae
        if current_mae is None or previous_mae is None or previous_mae <= 0:
            return None, "insufficient_history"

        ratio = current_mae / previous_mae
        if ratio >= self.drift_alert_ratio:
            return ratio, "worsened"
        if ratio <= Decimal("0.85"):
            return ratio, "improved"
        return ratio, "stable"


@dataclass(slots=True)
class ModelEvaluationBundle:
    evaluation: ModelEvaluationRecord
    residuals: list[Decimal]


def _with_forecast_metadata(forecast: ForecastResult, metadata: dict[str, str]) -> ForecastResult:
    return ForecastResult(
        item_id=forecast.item_id,
        horizon=forecast.horizon,
        forecast_created_at=forecast.forecast_created_at,
        forecast_target_at=forecast.forecast_target_at,
        predicted_mid_price=forecast.predicted_mid_price,
        model_name=forecast.model_name,
        model_version=forecast.model_version,
        metadata=metadata,
    )


@dataclass(slots=True)
class _Metrics:
    mae: Decimal
    rmse: Decimal
    smape: Decimal
    directional_accuracy: Decimal
    bias: Decimal


def _apply_liquidity_filter(
    observations: list[PriceObservation],
    *,
    minimum_liquidity_volume: int,
) -> tuple[list[PriceObservation], int]:
    filtered: list[PriceObservation] = []
    dropped = 0
    for observation in observations:
        high_volume = observation.high_price_volume
        low_volume = observation.low_price_volume
        if high_volume is None or low_volume is None:
            dropped += 1
            continue
        if high_volume < minimum_liquidity_volume or low_volume < minimum_liquidity_volume:
            dropped += 1
            continue
        filtered.append(observation)
    return filtered, dropped


def _prediction_interval_bounds(
    *,
    base_value: Decimal,
    residuals: list[Decimal],
    confidence: Decimal,
) -> tuple[Decimal, Decimal]:
    if not residuals:
        return base_value, base_value

    alpha = (Decimal("1") - confidence) / Decimal("2")
    low_q = _quantile(residuals, alpha)
    high_q = _quantile(residuals, Decimal("1") - alpha)
    return base_value + low_q, base_value + high_q


def _quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    n = len(sorted_values)
    scaled = probability * Decimal(n - 1)
    lower_index = int(scaled)
    upper_index = min(lower_index + 1, n - 1)
    fraction = scaled - Decimal(lower_index)
    lower = sorted_values[lower_index]
    upper = sorted_values[upper_index]
    return lower + (upper - lower) * fraction


def _compute_metrics(
    errors: list[Decimal],
    predictions: list[Decimal],
    targets: list[Decimal],
) -> _Metrics:
    count = Decimal(len(errors))
    abs_sum = sum(abs(err) for err in errors)
    sq_sum = sum(err * err for err in errors)
    bias = sum(errors) / count

    directional_hits = 0
    for idx in range(1, len(targets)):
        pred_direction = predictions[idx] - targets[idx - 1]
        actual_direction = targets[idx] - targets[idx - 1]
        if (pred_direction >= 0 and actual_direction >= 0) or (
            pred_direction < 0 and actual_direction < 0
        ):
            directional_hits += 1

    directional_denominator = max(1, len(targets) - 1)
    smape_acc = Decimal("0")
    for prediction, target in zip(predictions, targets, strict=True):
        denominator = abs(prediction) + abs(target)
        if denominator == 0:
            continue
        smape_acc += (abs(prediction - target) * Decimal("200")) / denominator

    return _Metrics(
        mae=abs_sum / count,
        rmse=Decimal(str(sqrt(float(sq_sum / count)))),
        smape=smape_acc / count,
        directional_accuracy=Decimal(directional_hits) / Decimal(directional_denominator),
        bias=bias,
    )
