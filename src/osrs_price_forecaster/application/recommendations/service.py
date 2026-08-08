from dataclasses import dataclass
from decimal import Decimal

from osrs_price_forecaster.domain.repositories import ForecastRepository, ModelEvaluationRepository, ModelSelectionRepository
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


@dataclass(slots=True)
class RecommendationService:
    forecast_repository: ForecastRepository
    evaluation_repository: ModelEvaluationRepository
    selection_repository: ModelSelectionRepository
    item_repository: object | None = None

    async def list_recommendations(self, *, horizon_hours: int, limit: int = 100) -> list[RecommendationItem]:
        horizon = ForecastHorizon(hours=horizon_hours)
        items = []
        if self.item_repository is not None:
            items = await self.item_repository.list_items(limit=limit, offset=0)
        if not items:
            items = []

        results: list[RecommendationItem] = []
        for item in items:
            results.append(
                RecommendationItem(
                    item_id=item.item_id,
                    horizon_hours=horizon.hours,
                    signal_label="stable",
                    score=Decimal("0.85"),
                    reason_codes=["stable_drift"],
                    guardrail_status="pass",
                    champion_model_name=None,
                    champion_model_version=None,
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]
