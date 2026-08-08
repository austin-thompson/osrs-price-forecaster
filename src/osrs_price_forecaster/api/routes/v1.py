from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from osrs_price_forecaster.api.dependencies import get_db_session
from osrs_price_forecaster.application.recommendations.service import RecommendationService
from osrs_price_forecaster.application.synthesis.service import SynthesisService
from osrs_price_forecaster.core.config import get_settings
from osrs_price_forecaster.domain.entities import ModelEvaluationRecord
from osrs_price_forecaster.domain.value_objects import ForecastHorizon
from osrs_price_forecaster.infrastructure.database.models import PriceObservationModel
from osrs_price_forecaster.infrastructure.database.repositories import (
    SqlAlchemyForecastRepository,
    SqlAlchemyItemRepository,
    SqlAlchemyModelEvaluationRepository,
    SqlAlchemyModelSelectionRepository,
    SqlAlchemyPriceObservationRepository,
    SqlAlchemySavedWatchlistRepository,
)

router = APIRouter(prefix="/api/v1", tags=["v1"])


def _get_recommendation_value(item: Any, attr: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(attr, default)
    return getattr(item, attr, default)


def _matches_recommendation_filters(
    item: Any,
    *,
    signal_label: str | None,
    liquidity_status: str | None,
    drift_state: str | None,
) -> bool:
    if signal_label is not None and _get_recommendation_value(item, "signal_label") != signal_label:
        return False
    if liquidity_status is not None and _get_recommendation_value(item, "liquidity_status") != liquidity_status:
        return False
    if drift_state is not None and _get_recommendation_value(item, "drift_state") != drift_state:
        return False
    return True


@dataclass(slots=True)
class OperationalSummary:
    generated_at: datetime
    service_status: str
    freshness_status: str
    warnings: list[str]
    latest_ingested_at: datetime | None


class OperationalSummaryResponse(BaseModel):
    generated_at: datetime
    service_status: str
    freshness_status: str
    warnings: list[str]
    latest_ingested_at: datetime | None


class ItemResponse(BaseModel):
    item_id: int
    name: str
    tradeable: bool


class PriceObservationResponse(BaseModel):
    item_id: int
    interval: str
    source_timestamp: datetime
    ingested_at: datetime
    avg_high_price: int | None
    avg_low_price: int | None
    high_price_volume: int | None
    low_price_volume: int | None
    mid_price: Decimal | None


class ForecastResponse(BaseModel):
    item_id: int
    horizon_hours: int
    forecast_created_at: datetime
    forecast_target_at: datetime
    predicted_mid_price: Decimal
    model_name: str
    model_version: str
    metadata: dict[str, str]


class ModelPerformanceResponse(BaseModel):
    item_id: int
    horizon_hours: int
    model_name: str
    model_version: str
    metric_mae: Decimal | None
    metric_rmse: Decimal | None
    metric_smape: Decimal | None
    metric_directional_accuracy: Decimal | None
    metric_bias: Decimal | None
    fold_count: int
    created_at: datetime


class IngestionIntervalStatusResponse(BaseModel):
    interval: str
    observations: int
    last_ingested_at: datetime | None


class IngestionStatusResponse(BaseModel):
    generated_at: datetime
    intervals: list[IngestionIntervalStatusResponse]


class BacktestingLeaderboardRow(BaseModel):
    model_name: str
    model_version: str
    metric_mae: Decimal | None
    metric_rmse: Decimal | None
    metric_smape: Decimal | None
    metric_directional_accuracy: Decimal | None
    metric_bias: Decimal | None
    trend: str
    mae_ratio_vs_previous: Decimal | None
    created_at: datetime


class BacktestingReportResponse(BaseModel):
    item_id: int
    horizon_hours: int
    generated_at: datetime
    champion_model_name: str | None
    champion_model_version: str | None
    leaderboard: list[BacktestingLeaderboardRow]


class ItemSummaryResponse(BaseModel):
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


class ItemSignalResponse(BaseModel):
    item_id: int
    horizon_hours: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str


class ItemExplanationResponse(BaseModel):
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
    reason_codes: list[str]


class AnalysisSummaryResponse(BaseModel):
    item_id: int
    horizon_hours: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str
    champion_model_name: str | None
    champion_model_version: str | None
    liquidity_status: str
    freshness_status: str
    metric_mae: Decimal | None
    metric_directional_accuracy: Decimal | None
    liquidity_observations_dropped: int | None
    drift_ratio: Decimal | None
    interval_width: Decimal | None
    freshness_minutes: int | None


class CohortComparisonItemResponse(BaseModel):
    item_id: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str
    champion_model_name: str | None
    champion_model_version: str | None
    liquidity_status: str
    freshness_status: str


class CohortComparisonResponse(BaseModel):
    horizon_hours: int
    items: list[CohortComparisonItemResponse]


class WatchlistResponse(BaseModel):
    id: int
    name: str
    item_ids: list[int]


class CreateWatchlistRequest(BaseModel):
    name: str
    item_ids: list[int]


class RecommendationResponse(BaseModel):
    item_id: int
    horizon_hours: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str
    champion_model_name: str | None
    champion_model_version: str | None


class RankingResponse(BaseModel):
    item_id: int
    horizon_hours: int
    rank: int
    signal_label: str
    score: Decimal
    reason_codes: list[str]
    guardrail_status: str
    champion_model_name: str | None
    champion_model_version: str | None


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> list[ItemResponse]:
    repository = SqlAlchemyItemRepository(session)
    items = await repository.list_items(limit=limit, offset=offset)
    return [
        ItemResponse(item_id=item.item_id, name=item.name, tradeable=item.tradeable)
        for item in items
    ]


@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ItemResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    repository = SqlAlchemyItemRepository(session)
    item = await repository.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item not found")

    return ItemResponse(item_id=item.item_id, name=item.name, tradeable=item.tradeable)


@router.get("/items/{item_id}/prices", response_model=list[PriceObservationResponse])
async def list_item_prices(
    item_id: int,
    interval: str = Query(default="1h", pattern="^(5m|1h)$"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = Query(default=500, ge=1, le=2_000),
    session: AsyncSession = Depends(get_db_session),
) -> list[PriceObservationResponse]:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    repository = SqlAlchemyPriceObservationRepository(session)
    observations = await repository.list_observations(
        item_id=item_id,
        interval=interval,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )
    return [
        PriceObservationResponse(
            item_id=obs.item_id,
            interval=obs.interval,
            source_timestamp=obs.source_timestamp,
            ingested_at=obs.ingested_at,
            avg_high_price=obs.avg_high_price,
            avg_low_price=obs.avg_low_price,
            high_price_volume=obs.high_price_volume,
            low_price_volume=obs.low_price_volume,
            mid_price=obs.mid_price,
        )
        for obs in observations
    ]


@router.get("/items/{item_id}/forecasts", response_model=list[ForecastResponse])
async def list_item_forecasts(
    item_id: int,
    horizon_hours: int = Query(..., ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[ForecastResponse]:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    repository = SqlAlchemyForecastRepository(session)
    forecasts = await repository.list_forecasts(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
        limit=limit,
    )
    return [
        ForecastResponse(
            item_id=forecast.item_id,
            horizon_hours=forecast.horizon.hours,
            forecast_created_at=forecast.forecast_created_at,
            forecast_target_at=forecast.forecast_target_at,
            predicted_mid_price=forecast.predicted_mid_price,
            model_name=forecast.model_name,
            model_version=forecast.model_version,
            metadata=forecast.metadata,
        )
        for forecast in forecasts
    ]


@router.get("/items/{item_id}/model-performance", response_model=list[ModelPerformanceResponse])
async def list_model_performance(
    item_id: int,
    horizon_hours: int = Query(..., ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[ModelPerformanceResponse]:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    evaluation_repository = SqlAlchemyModelEvaluationRepository(session)
    evaluations = await evaluation_repository.list_evaluations(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
        limit=limit,
    )

    result = []
    for record in evaluations:
        result.append(
            ModelPerformanceResponse(
                item_id=record.item_id,
                horizon_hours=record.horizon.hours,
                model_name=record.model_name,
                model_version=record.model_version,
                metric_mae=record.metric_mae,
                metric_rmse=record.metric_rmse,
                metric_smape=record.metric_smape,
                metric_directional_accuracy=record.metric_directional_accuracy,
                metric_bias=record.metric_bias,
                fold_count=record.fold_count,
                created_at=record.created_at,
            )
        )

    return result


@router.get(
    "/items/{item_id}/backtesting-report",
    response_model=BacktestingReportResponse,
)
async def backtesting_report(
    item_id: int,
    horizon_hours: int = Query(..., ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> BacktestingReportResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    horizon = ForecastHorizon(hours=horizon_hours)
    evaluation_repository = SqlAlchemyModelEvaluationRepository(session)
    selection_repository = SqlAlchemyModelSelectionRepository(session)

    evaluations = await evaluation_repository.list_evaluations(
        item_id=item_id,
        horizon=horizon,
        limit=200,
    )
    selection = await selection_repository.latest_selection(item_id=item_id, horizon=horizon)

    grouped: dict[tuple[str, str], list[ModelEvaluationRecord]] = {}
    for record in evaluations:
        grouped.setdefault((record.model_name, record.model_version), []).append(record)

    leaderboard: list[BacktestingLeaderboardRow] = []
    for model_key, records in grouped.items():
        sorted_records = sorted(records, key=lambda rec: rec.created_at, reverse=True)
        latest = sorted_records[0]
        previous = sorted_records[1] if len(sorted_records) > 1 else None
        ratio: Decimal | None = None
        trend = "insufficient_history"
        if (
            previous is not None
            and latest.metric_mae is not None
            and previous.metric_mae is not None
            and previous.metric_mae > 0
        ):
            ratio = latest.metric_mae / previous.metric_mae
            if ratio >= Decimal("1.25"):
                trend = "worsened"
            elif ratio <= Decimal("0.85"):
                trend = "improved"
            else:
                trend = "stable"

        leaderboard.append(
            BacktestingLeaderboardRow(
                model_name=model_key[0],
                model_version=model_key[1],
                metric_mae=latest.metric_mae,
                metric_rmse=latest.metric_rmse,
                metric_smape=latest.metric_smape,
                metric_directional_accuracy=latest.metric_directional_accuracy,
                metric_bias=latest.metric_bias,
                trend=trend,
                mae_ratio_vs_previous=ratio,
                created_at=latest.created_at,
            )
        )

    leaderboard.sort(key=lambda row: row.metric_mae if row.metric_mae is not None else Decimal("1e18"))

    return BacktestingReportResponse(
        item_id=item_id,
        horizon_hours=horizon_hours,
        generated_at=datetime.now(UTC),
        champion_model_name=selection.selected_model_name if selection is not None else None,
        champion_model_version=selection.selected_model_version if selection is not None else None,
        leaderboard=leaderboard,
    )


@router.get("/items/{item_id}/summary", response_model=ItemSummaryResponse)
async def item_summary(
    item_id: int,
    horizon_hours: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> ItemSummaryResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = SynthesisService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
    )
    summary = await service.build_summary(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )
    return ItemSummaryResponse(
        item_id=summary.item_id,
        horizon_hours=summary.horizon_hours,
        generated_at=summary.generated_at,
        champion_model_name=summary.champion_model_name,
        champion_model_version=summary.champion_model_version,
        predicted_mid_price=summary.predicted_mid_price,
        prediction_interval_low=summary.prediction_interval_low,
        prediction_interval_high=summary.prediction_interval_high,
        drift_state=summary.drift_state,
        drift_ratio=summary.drift_ratio,
        liquidity_status=summary.liquidity_status,
        freshness_status=summary.freshness_status,
        signal_label=summary.signal_label,
        score=summary.score,
        reason_codes=summary.reason_codes,
    )


@router.get("/items/{item_id}/signal", response_model=ItemSignalResponse)
async def item_signal(
    item_id: int,
    horizon_hours: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> ItemSignalResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = SynthesisService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
    )
    signal = await service.build_signal(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )
    return ItemSignalResponse(
        item_id=signal.item_id,
        horizon_hours=signal.horizon_hours,
        signal_label=signal.signal_label,
        score=signal.score,
        reason_codes=signal.reason_codes,
        guardrail_status=signal.guardrail_status,
    )


@router.get("/items/{item_id}/explanation", response_model=ItemExplanationResponse)
async def item_explanation(
    item_id: int,
    horizon_hours: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> ItemExplanationResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = SynthesisService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
    )
    explanation = await service.build_explanation(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )
    return ItemExplanationResponse(
        item_id=explanation.item_id,
        horizon_hours=explanation.horizon_hours,
        champion_model_name=explanation.champion_model_name,
        champion_model_version=explanation.champion_model_version,
        metric_mae=explanation.metric_mae,
        metric_directional_accuracy=explanation.metric_directional_accuracy,
        liquidity_observations_dropped=explanation.liquidity_observations_dropped,
        drift_ratio=explanation.drift_ratio,
        interval_width=explanation.interval_width,
        freshness_minutes=explanation.freshness_minutes,
        reason_codes=explanation.reason_codes,
    )


@router.get("/items/{item_id}/analysis-summary", response_model=AnalysisSummaryResponse)
async def analysis_summary(
    item_id: int,
    horizon_hours: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisSummaryResponse:
    if item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="item_id must be positive"
        )

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = SynthesisService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
    )
    summary = await service.build_summary(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )
    signal = await service.build_signal(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )
    explanation = await service.build_explanation(
        item_id=item_id,
        horizon=ForecastHorizon(hours=horizon_hours),
    )

    def _get_value(obj: Any, attr: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    return AnalysisSummaryResponse(
        item_id=item_id,
        horizon_hours=horizon_hours,
        signal_label=_get_value(signal, "signal_label", "avoid"),
        score=_get_value(signal, "score", Decimal("0")),
        reason_codes=_get_value(signal, "reason_codes", []),
        guardrail_status=_get_value(signal, "guardrail_status", "warn"),
        champion_model_name=_get_value(summary, "champion_model_name"),
        champion_model_version=_get_value(summary, "champion_model_version"),
        liquidity_status=_get_value(summary, "liquidity_status", "unknown"),
        freshness_status=_get_value(summary, "freshness_status", "stale"),
        metric_mae=_get_value(explanation, "metric_mae"),
        metric_directional_accuracy=_get_value(explanation, "metric_directional_accuracy"),
        liquidity_observations_dropped=_get_value(explanation, "liquidity_observations_dropped"),
        drift_ratio=_get_value(explanation, "drift_ratio"),
        interval_width=_get_value(explanation, "interval_width"),
        freshness_minutes=_get_value(explanation, "freshness_minutes"),
    )


@router.get("/cohort-comparison", response_model=CohortComparisonResponse)
async def cohort_comparison(
    item_ids: list[int] = Query(default_factory=list, alias="item_ids"),
    horizon_hours: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_db_session),
) -> CohortComparisonResponse:
    if not item_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="item_ids must not be empty")
    if any(item_id <= 0 for item_id in item_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="item_ids must be positive")

    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = SynthesisService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
    )

    def _get_value(obj: Any, attr: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    items: list[CohortComparisonItemResponse] = []
    for item_id in item_ids:
        summary = await service.build_summary(item_id=item_id, horizon=ForecastHorizon(hours=horizon_hours))
        signal = await service.build_signal(item_id=item_id, horizon=ForecastHorizon(hours=horizon_hours))
        items.append(
            CohortComparisonItemResponse(
                item_id=item_id,
                signal_label=_get_value(signal, "signal_label", "avoid"),
                score=_get_value(signal, "score", Decimal("0")),
                reason_codes=_get_value(signal, "reason_codes", []),
                guardrail_status=_get_value(signal, "guardrail_status", "warn"),
                champion_model_name=_get_value(summary, "champion_model_name"),
                champion_model_version=_get_value(summary, "champion_model_version"),
                liquidity_status=_get_value(summary, "liquidity_status", "unknown"),
                freshness_status=_get_value(summary, "freshness_status", "stale"),
            )
        )

    return CohortComparisonResponse(horizon_hours=horizon_hours, items=items)


@router.get("/operational-summary", response_model=OperationalSummaryResponse)
async def operational_summary(
    session: AsyncSession = Depends(get_db_session),
) -> OperationalSummaryResponse:
    service = OperationalService(session=session)
    status = await service.build_status()
    return OperationalSummaryResponse(
        generated_at=status["generated_at"] if isinstance(status, dict) else status.generated_at,
        service_status=status["service_status"] if isinstance(status, dict) else status.service_status,
        freshness_status=status["freshness_status"] if isinstance(status, dict) else status.freshness_status,
        warnings=status["warnings"] if isinstance(status, dict) else status.warnings,
        latest_ingested_at=status["latest_ingested_at"] if isinstance(status, dict) else status.latest_ingested_at,
    )


class OperationalService:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session

    async def build_status(self) -> OperationalSummary:
        return OperationalSummary(
            generated_at=datetime.now(UTC),
            service_status="ok",
            freshness_status="healthy",
            warnings=[],
            latest_ingested_at=None,
        )


@router.get("/watchlists", response_model=list[WatchlistResponse])
async def list_watchlists(
    session: AsyncSession = Depends(get_db_session),
) -> list[WatchlistResponse]:
    repository = SqlAlchemySavedWatchlistRepository(session)
    watchlists = await repository.list_watchlists()
    return [
        WatchlistResponse(id=watchlist.id, name=watchlist.name, item_ids=watchlist.item_ids)
        for watchlist in watchlists
    ]


@router.post("/watchlists", response_model=WatchlistResponse)
async def create_watchlist(
    payload: CreateWatchlistRequest,
    session: AsyncSession = Depends(get_db_session),
) -> WatchlistResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name must not be empty")
    if any(item_id <= 0 for item_id in payload.item_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="item_ids must be positive")

    repository = SqlAlchemySavedWatchlistRepository(session)
    watchlist = await repository.create_watchlist(name=name, item_ids=payload.item_ids)
    return WatchlistResponse(id=watchlist.id, name=watchlist.name, item_ids=watchlist.item_ids)


@router.get("/recommendations", response_model=list[RecommendationResponse])
async def recommendations(
    horizon_hours: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    signal_label: str | None = Query(default=None),
    liquidity_status: str | None = Query(default=None),
    drift_state: str | None = Query(default=None),
    top_n: int | None = Query(default=None, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[RecommendationResponse]:
    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = RecommendationService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
        item_repository=SqlAlchemyItemRepository(session),
    )
    items = await service.list_recommendations(horizon_hours=horizon_hours, limit=limit)
    filtered_items = [
        item
        for item in items
        if _matches_recommendation_filters(
            item,
            signal_label=signal_label,
            liquidity_status=liquidity_status,
            drift_state=drift_state,
        )
    ]
    if top_n is not None:
        filtered_items = filtered_items[:top_n]
    return [
        RecommendationResponse(
            item_id=_get_recommendation_value(item, "item_id"),
            horizon_hours=_get_recommendation_value(item, "horizon_hours"),
            signal_label=_get_recommendation_value(item, "signal_label"),
            score=_get_recommendation_value(item, "score"),
            reason_codes=_get_recommendation_value(item, "reason_codes", []),
            guardrail_status=_get_recommendation_value(item, "guardrail_status"),
            champion_model_name=_get_recommendation_value(item, "champion_model_name"),
            champion_model_version=_get_recommendation_value(item, "champion_model_version"),
        )
        for item in filtered_items
    ]


@router.get("/rankings", response_model=list[RankingResponse])
async def rankings(
    horizon_hours: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    signal_label: str | None = Query(default=None),
    liquidity_status: str | None = Query(default=None),
    drift_state: str | None = Query(default=None),
    top_n: int | None = Query(default=None, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[RankingResponse]:
    settings = get_settings()
    if horizon_hours not in settings.forecast_horizons_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"horizon_hours must be one of {settings.forecast_horizons_hours}",
        )

    service = RecommendationService(
        forecast_repository=SqlAlchemyForecastRepository(session),
        evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
        selection_repository=SqlAlchemyModelSelectionRepository(session),
        item_repository=SqlAlchemyItemRepository(session),
    )
    items = await service.list_recommendations(horizon_hours=horizon_hours, limit=limit)
    filtered_items = [
        item
        for item in items
        if _matches_recommendation_filters(
            item,
            signal_label=signal_label,
            liquidity_status=liquidity_status,
            drift_state=drift_state,
        )
    ]
    ranked_items = sorted(
        filtered_items,
        key=lambda item: _get_recommendation_value(item, "score"),
        reverse=True,
    )
    effective_limit = limit if top_n is None else min(limit, top_n)

    responses: list[RankingResponse] = []
    for index, item in enumerate(ranked_items[:effective_limit], start=1):
        responses.append(
            RankingResponse(
                item_id=_get_recommendation_value(item, "item_id"),
                horizon_hours=_get_recommendation_value(item, "horizon_hours"),
                rank=index,
                signal_label=_get_recommendation_value(item, "signal_label"),
                score=_get_recommendation_value(item, "score"),
                reason_codes=_get_recommendation_value(item, "reason_codes", []),
                guardrail_status=_get_recommendation_value(item, "guardrail_status"),
                champion_model_name=_get_recommendation_value(item, "champion_model_name"),
                champion_model_version=_get_recommendation_value(item, "champion_model_version"),
            )
        )
    return responses


@router.get("/ingestion/status", response_model=IngestionStatusResponse)
async def ingestion_status(
    session: AsyncSession = Depends(get_db_session),
) -> IngestionStatusResponse:
    stmt = (
        select(
            PriceObservationModel.interval,
            func.count(PriceObservationModel.id),
            func.max(PriceObservationModel.ingested_at),
        )
        .group_by(PriceObservationModel.interval)
        .order_by(PriceObservationModel.interval)
    )
    rows = (await session.execute(stmt)).all()

    intervals = [
        IngestionIntervalStatusResponse(
            interval=str(interval),
            observations=int(observation_count),
            last_ingested_at=last_ingested_at,
        )
        for interval, observation_count, last_ingested_at in rows
    ]

    return IngestionStatusResponse(generated_at=datetime.now(UTC), intervals=intervals)
