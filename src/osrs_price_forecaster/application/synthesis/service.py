from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    ModelEvaluationRecord,
)
from osrs_price_forecaster.domain.repositories import (
    ForecastRepository,
    ModelEvaluationRepository,
    ModelSelectionRepository,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


@dataclass(slots=True)
class ItemSummary:
    item_id: int
    horizon_hours: int
    generated_at: datetime
    champion_model_name: str | None
    champion_model_version: str | None
    predicted_mid_price: Decimal | None
    prediction_interval_low: Decimal | None
    prediction_interval_high: Decimal | None
    drift_state: str | None
    drift_ratio: Decimal | None
    liquidity_status: str
    freshness_status: str
    signal_label: str
    score: Decimal
    reason_codes: list[str]


@dataclass(slots=True)
class ItemSignal:
    item_id: int
    horizon_hours: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str


@dataclass(slots=True)
class ItemExplanation:
    item_id: int
    horizon_hours: int
    champion_model_name: str | None
    champion_model_version: str | None
    metric_mae: Decimal | None
    metric_directional_accuracy: Decimal | None
    liquidity_observations_dropped: int | None
    drift_ratio: Decimal | None
    interval_width: Decimal | None
    freshness_minutes: int | None
    drift_state: str
    liquidity_status: str
    freshness_status: str
    reason_codes: list[str]
    evidence_summary: list[str]


@dataclass(slots=True)
class SynthesisService:
    forecast_repository: ForecastRepository
    evaluation_repository: ModelEvaluationRepository
    selection_repository: ModelSelectionRepository
    freshness_threshold_minutes: int = 180
    liquidity_drop_threshold: int = 3
    confidence_band_threshold_ratio: Decimal = Decimal("0.25")
    score_floor: Decimal = Decimal("0.0")

    async def build_summary(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ItemSummary:
        forecast = await self._latest_forecast(item_id=item_id, horizon=horizon)
        selection = await self.selection_repository.latest_selection(
            item_id=item_id, horizon=horizon
        )

        signal = await self.build_signal(item_id=item_id, horizon=horizon)
        reason_codes = signal.reason_codes
        liquidity_status = self._derive_liquidity_status(forecast)
        freshness_status = self._derive_freshness_status(forecast)

        metadata = forecast.metadata if forecast is not None else {}
        interval_low = self._decimal_from_metadata(metadata, "prediction_interval_low")
        interval_high = self._decimal_from_metadata(metadata, "prediction_interval_high")
        drift_state = forecast.metadata.get("drift_state") if forecast is not None else None
        drift_ratio = self._decimal_from_metadata(metadata, "drift_ratio")

        return ItemSummary(
            item_id=item_id,
            horizon_hours=horizon.hours,
            generated_at=datetime.now(UTC),
            champion_model_name=selection.selected_model_name if selection is not None else None,
            champion_model_version=selection.selected_model_version
            if selection is not None
            else None,
            predicted_mid_price=forecast.predicted_mid_price if forecast is not None else None,
            prediction_interval_low=interval_low,
            prediction_interval_high=interval_high,
            drift_state=drift_state,
            drift_ratio=drift_ratio,
            liquidity_status=liquidity_status,
            freshness_status=freshness_status,
            signal_label=signal.signal_label,
            score=signal.score,
            reason_codes=reason_codes,
        )

    async def build_signal(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ItemSignal:
        forecast = await self._latest_forecast(item_id=item_id, horizon=horizon)
        evaluation = await self._latest_evaluation(item_id=item_id, horizon=horizon)
        selection = await self.selection_repository.latest_selection(
            item_id=item_id, horizon=horizon
        )

        if forecast is None:
            return ItemSignal(
                item_id=item_id,
                horizon_hours=horizon.hours,
                signal_label="avoid",
                score=Decimal("0.0"),
                reason_codes=["missing_forecast"],
                guardrail_status="blocked",
            )

        reason_codes: list[str] = []
        score = Decimal("0.7")
        liquidity_status = self._derive_liquidity_status(forecast)
        freshness_status = self._derive_freshness_status(forecast)
        drift_state = forecast.metadata.get("drift_state", "unknown")
        interval_low = self._decimal_from_metadata(forecast.metadata, "prediction_interval_low")
        interval_high = self._decimal_from_metadata(forecast.metadata, "prediction_interval_high")
        interval_width = None
        if interval_low is not None and interval_high is not None:
            interval_width = abs(interval_high - interval_low)

        if freshness_status == "stale":
            reason_codes.append("stale_data")
            score -= Decimal("0.25")
        if liquidity_status != "healthy":
            reason_codes.append("liquidity_risk")
            score -= Decimal("0.25")
        if drift_state == "worsened":
            reason_codes.append("drift_worsened")
            score -= Decimal("0.15")
        elif drift_state == "improved":
            reason_codes.append("drift_improved")
            score += Decimal("0.05")
        if interval_width is not None and interval_width > 0:
            ratio = interval_width / max(forecast.predicted_mid_price, Decimal("1"))
            if ratio >= self.confidence_band_threshold_ratio:
                reason_codes.append("wide_interval")
                score -= Decimal("0.10")

        if evaluation is not None and evaluation.metric_mae is not None:
            if evaluation.metric_mae > Decimal("100"):
                reason_codes.append("weak_model_quality")
                score -= Decimal("0.10")

        if selection is None:
            reason_codes.append("missing_selection")
            score -= Decimal("0.10")

        score = max(self.score_floor, min(Decimal("1.0"), score))
        if score < Decimal("0.35"):
            signal_label = "avoid"
        elif score < Decimal("0.65"):
            signal_label = "caution"
        else:
            signal_label = "stable"

        return ItemSignal(
            item_id=item_id,
            horizon_hours=horizon.hours,
            signal_label=signal_label,
            score=score,
            reason_codes=reason_codes,
            guardrail_status="pass" if not reason_codes else "warn",
        )

    async def build_explanation(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ItemExplanation:
        forecast = await self._latest_forecast(item_id=item_id, horizon=horizon)
        evaluation = await self._latest_evaluation(item_id=item_id, horizon=horizon)
        selection = await self.selection_repository.latest_selection(
            item_id=item_id, horizon=horizon
        )

        freshness_minutes = None
        if forecast is not None:
            freshness_minutes = int(
                (datetime.now(UTC) - forecast.forecast_created_at).total_seconds() // 60
            )

        liquidity_observations_dropped = None
        if forecast is not None:
            liquidity_observations_dropped = self._int_from_metadata(
                forecast.metadata, "liquidity_observations_dropped"
            )

        metadata = forecast.metadata if forecast is not None else {}
        interval_low = self._decimal_from_metadata(metadata, "prediction_interval_low")
        interval_high = self._decimal_from_metadata(metadata, "prediction_interval_high")
        interval_width = None
        if interval_low is not None and interval_high is not None:
            interval_width = abs(interval_high - interval_low)

        drift_ratio = self._decimal_from_metadata(metadata, "drift_ratio")
        drift_state = metadata.get("drift_state", "unknown")
        liquidity_status = self._derive_liquidity_status(forecast)
        freshness_status = self._derive_freshness_status(forecast)
        reason_codes = []
        if forecast is None:
            reason_codes.append("missing_forecast")
        else:
            if freshness_status == "stale":
                reason_codes.append("stale_data")
            if liquidity_status != "healthy":
                reason_codes.append("liquidity_risk")
            if drift_state == "worsened":
                reason_codes.append("drift_worsened")

        evidence_summary = self._build_evidence_summary(
            forecast_present=forecast is not None,
            selection_present=selection is not None,
            evaluation_present=evaluation is not None,
            drift_state=drift_state,
            liquidity_status=liquidity_status,
            freshness_status=freshness_status,
        )

        return ItemExplanation(
            item_id=item_id,
            horizon_hours=horizon.hours,
            champion_model_name=selection.selected_model_name if selection is not None else None,
            champion_model_version=selection.selected_model_version
            if selection is not None
            else None,
            metric_mae=evaluation.metric_mae if evaluation is not None else None,
            metric_directional_accuracy=evaluation.metric_directional_accuracy
            if evaluation is not None
            else None,
            liquidity_observations_dropped=liquidity_observations_dropped,
            drift_ratio=drift_ratio,
            interval_width=interval_width,
            freshness_minutes=freshness_minutes,
            drift_state=drift_state,
            liquidity_status=liquidity_status,
            freshness_status=freshness_status,
            reason_codes=reason_codes,
            evidence_summary=evidence_summary,
        )

    def _build_evidence_summary(
        self,
        *,
        forecast_present: bool,
        selection_present: bool,
        evaluation_present: bool,
        drift_state: str,
        liquidity_status: str,
        freshness_status: str,
    ) -> list[str]:
        if not forecast_present:
            return ["No current forecast is available for this item and horizon."]

        statements = [
            f"Forecast freshness is {freshness_status}.",
            f"Liquidity evidence is {liquidity_status}.",
            f"Recent model drift is {drift_state}.",
        ]
        if not selection_present:
            statements.append("No champion model selection is available.")
        if not evaluation_present:
            statements.append("No recent model evaluation is available.")
        return statements

    async def _latest_forecast(
        self, *, item_id: int, horizon: ForecastHorizon
    ) -> ForecastResult | None:
        forecasts = await self.forecast_repository.list_forecasts(
            item_id=item_id, horizon=horizon, limit=1
        )
        return forecasts[0] if forecasts else None

    async def _latest_evaluation(
        self, *, item_id: int, horizon: ForecastHorizon
    ) -> ModelEvaluationRecord | None:
        evaluations = await self.evaluation_repository.list_evaluations(
            item_id=item_id, horizon=horizon, limit=1
        )
        return evaluations[0] if evaluations else None

    def _derive_liquidity_status(self, forecast: ForecastResult | None) -> str:
        if forecast is None:
            return "unknown"
        dropped = self._int_from_metadata(forecast.metadata, "liquidity_observations_dropped")
        if dropped is None:
            return "unknown"
        if dropped >= self.liquidity_drop_threshold:
            return "risky"
        return "healthy"

    def _derive_freshness_status(self, forecast: ForecastResult | None) -> str:
        if forecast is None:
            return "stale"
        age_minutes = int((datetime.now(UTC) - forecast.forecast_created_at).total_seconds() // 60)
        if age_minutes >= self.freshness_threshold_minutes:
            return "stale"
        if age_minutes >= self.freshness_threshold_minutes // 2:
            return "warning"
        return "fresh"

    def _decimal_from_metadata(self, metadata: dict[str, str], key: str) -> Decimal | None:
        value = metadata.get(key)
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _int_from_metadata(self, metadata: dict[str, str], key: str) -> int | None:
        value = metadata.get(key)
        if value is None:
            return None
        try:
            return int(str(value))
        except Exception:
            return None
