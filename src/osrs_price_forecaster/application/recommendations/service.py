from dataclasses import dataclass
from decimal import Decimal

from osrs_price_forecaster.application.synthesis.service import SynthesisService
from osrs_price_forecaster.domain.repositories import (
    ForecastRepository,
    ItemRepository,
    ModelEvaluationRepository,
    ModelSelectionRepository,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


@dataclass(slots=True)
class RecommendationItem:
    item_id: int
    horizon_hours: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str
    champion_model_name: str | None
    champion_model_version: str | None
    liquidity_status: str | None = None
    drift_state: str | None = None


@dataclass(slots=True)
class RecommendationService:
    forecast_repository: ForecastRepository
    evaluation_repository: ModelEvaluationRepository
    selection_repository: ModelSelectionRepository
    item_repository: ItemRepository | None = None

    async def list_recommendations(
        self, *, horizon_hours: int, limit: int = 100
    ) -> list[RecommendationItem]:
        horizon = ForecastHorizon(hours=horizon_hours)
        items = []
        if self.item_repository is not None:
            items = await self.item_repository.list_items(limit=limit, offset=0)
        if not items:
            return []

        synthesis_service = SynthesisService(
            forecast_repository=self.forecast_repository,
            evaluation_repository=self.evaluation_repository,
            selection_repository=self.selection_repository,
        )

        results: list[RecommendationItem] = []
        for item in items:
            summary = await synthesis_service.build_summary(item_id=item.item_id, horizon=horizon)
            selection = await self.selection_repository.latest_selection(
                item_id=item.item_id, horizon=horizon
            )
            results.append(
                RecommendationItem(
                    item_id=item.item_id,
                    horizon_hours=horizon.hours,
                    signal_label=summary.signal_label,
                    score=summary.score,
                    reason_codes=summary.reason_codes,
                    guardrail_status="pass" if summary.signal_label == "stable" else "warn",
                    champion_model_name=selection.selected_model_name
                    if selection is not None
                    else None,
                    champion_model_version=selection.selected_model_version
                    if selection is not None
                    else None,
                    liquidity_status=summary.liquidity_status,
                    drift_state=summary.drift_state,
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]
