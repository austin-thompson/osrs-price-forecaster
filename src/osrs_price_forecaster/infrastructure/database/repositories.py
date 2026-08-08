from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    Item,
    ModelEvaluationRecord,
    ModelSelectionRecord,
    PriceObservation,
    Watchlist,
)
from osrs_price_forecaster.domain.repositories import (
    ForecastRepository,
    ItemRepository,
    ModelEvaluationRepository,
    ModelSelectionRepository,
    PriceObservationRepository,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon
from osrs_price_forecaster.infrastructure.database.models import (
    ForecastModel,
    ItemModel,
    ModelEvaluationModel,
    ModelSelectionModel,
    PriceObservationModel,
    SavedWatchlistModel,
)


class SqlAlchemyItemRepository(ItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_item(self, item_id: int) -> Item | None:
        result = await self._session.execute(select(ItemModel).where(ItemModel.item_id == item_id))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return Item(item_id=row.item_id, name=row.name, tradeable=row.tradeable)

    async def list_items(self, limit: int = 100, offset: int = 0) -> list[Item]:
        stmt = select(ItemModel).order_by(ItemModel.item_id).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [Item(item_id=row.item_id, name=row.name, tradeable=row.tradeable) for row in rows]

    async def upsert_items(self, items: Sequence[Item]) -> int:
        if not items:
            return 0

        stmt = insert(ItemModel).values(
            [
                {
                    "item_id": item.item_id,
                    "name": item.name,
                    "tradeable": item.tradeable,
                    "first_seen_at": datetime.now(UTC),
                    "last_seen_at": datetime.now(UTC),
                }
                for item in items
            ]
        )
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[ItemModel.item_id],
            set_={
                "name": stmt.excluded.name,
                "tradeable": stmt.excluded.tradeable,
                "last_seen_at": datetime.now(UTC),
            },
        )
        await self._session.execute(upsert_stmt)
        await self._session.commit()
        return len(items)


class SqlAlchemySavedWatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_watchlists(self) -> list[Watchlist]:
        stmt = select(SavedWatchlistModel).order_by(
            SavedWatchlistModel.created_at.desc(), SavedWatchlistModel.id.desc()
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            Watchlist(id=row.id, name=row.name, item_ids=list(row.item_ids or [])) for row in rows
        ]

    async def create_watchlist(self, *, name: str, item_ids: list[int]) -> Watchlist:
        record = SavedWatchlistModel(name=name, item_ids=list(item_ids))
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return Watchlist(id=record.id, name=record.name, item_ids=list(record.item_ids or []))


class SqlAlchemyPriceObservationRepository(PriceObservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_observations(self, observations: Sequence[PriceObservation]) -> int:
        if not observations:
            return 0

        values = []
        for obs in observations:
            values.append(
                {
                    "item_id": obs.item_id,
                    "interval": obs.interval,
                    "source_timestamp": obs.source_timestamp,
                    "ingested_at": obs.ingested_at,
                    "avg_high_price": obs.avg_high_price,
                    "avg_low_price": obs.avg_low_price,
                    "high_price_volume": obs.high_price_volume,
                    "low_price_volume": obs.low_price_volume,
                    "mid_price": obs.mid_price,
                }
            )

        stmt = insert(PriceObservationModel).values(values)
        upsert_stmt = stmt.on_conflict_do_update(
            constraint="uq_price_observations_item_interval_source_timestamp",
            set_={
                "ingested_at": stmt.excluded.ingested_at,
                "avg_high_price": stmt.excluded.avg_high_price,
                "avg_low_price": stmt.excluded.avg_low_price,
                "high_price_volume": stmt.excluded.high_price_volume,
                "low_price_volume": stmt.excluded.low_price_volume,
                "mid_price": stmt.excluded.mid_price,
            },
        )
        await self._session.execute(upsert_stmt)
        await self._session.commit()
        return len(observations)

    async def list_observations(
        self,
        item_id: int,
        interval: str,
        start_at: datetime | None,
        end_at: datetime | None,
        limit: int = 500,
    ) -> list[PriceObservation]:
        stmt = select(PriceObservationModel).where(
            PriceObservationModel.item_id == item_id,
            PriceObservationModel.interval == interval,
        )
        if start_at is not None:
            stmt = stmt.where(PriceObservationModel.source_timestamp >= start_at)
        if end_at is not None:
            stmt = stmt.where(PriceObservationModel.source_timestamp <= end_at)

        stmt = stmt.order_by(desc(PriceObservationModel.source_timestamp)).limit(limit)

        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            PriceObservation(
                item_id=row.item_id,
                interval=row.interval,
                source_timestamp=row.source_timestamp,
                ingested_at=row.ingested_at,
                avg_high_price=row.avg_high_price,
                avg_low_price=row.avg_low_price,
                high_price_volume=row.high_price_volume,
                low_price_volume=row.low_price_volume,
                mid_price=row.mid_price,
            )
            for row in rows
        ]


class SqlAlchemyForecastRepository(ForecastRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_forecast(self, forecast: ForecastResult) -> int:
        stmt = insert(ForecastModel).values(
            {
                "item_id": forecast.item_id,
                "horizon_hours": forecast.horizon.hours,
                "interval": "1h",
                "forecast_created_at": forecast.forecast_created_at,
                "forecast_target_at": forecast.forecast_target_at,
                "predicted_mid_price": Decimal(forecast.predicted_mid_price),
                "model_name": forecast.model_name,
                "model_version": forecast.model_version,
                "metadata_json": dict(forecast.metadata),
            }
        )

        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_forecasts_item_horizon_created_target_model"
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return 1

    async def list_forecasts(
        self,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ForecastResult]:
        stmt = (
            select(ForecastModel)
            .where(ForecastModel.item_id == item_id, ForecastModel.horizon_hours == horizon.hours)
            .order_by(desc(ForecastModel.forecast_created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            ForecastResult(
                item_id=row.item_id,
                horizon=horizon,
                forecast_created_at=row.forecast_created_at,
                forecast_target_at=row.forecast_target_at,
                predicted_mid_price=Decimal(row.predicted_mid_price),
                model_name=row.model_name,
                model_version=row.model_version,
                metadata={str(k): str(v) for k, v in row.metadata_json.items()},
            )
            for row in rows
        ]


class SqlAlchemyModelEvaluationRepository(ModelEvaluationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        record = ModelEvaluationModel(
            item_id=item_id,
            horizon_hours=horizon.hours,
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
            metadata_json=dict(metadata),
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return _evaluation_model_to_record(record)

    async def list_evaluations(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ModelEvaluationRecord]:
        stmt = (
            select(ModelEvaluationModel)
            .where(
                ModelEvaluationModel.item_id == item_id,
                ModelEvaluationModel.horizon_hours == horizon.hours,
            )
            .order_by(desc(ModelEvaluationModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_evaluation_model_to_record(row) for row in rows]


class SqlAlchemyModelSelectionRepository(ModelSelectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        record = ModelSelectionModel(
            item_id=item_id,
            horizon_hours=horizon.hours,
            selected_model_name=selected_model_name,
            selected_model_version=selected_model_version,
            primary_metric=primary_metric,
            primary_metric_value=primary_metric_value,
            reason=reason,
            selected_at=selected_at,
            evaluation_id=evaluation_id,
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return _selection_model_to_record(record)

    async def latest_selection(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ModelSelectionRecord | None:
        stmt = (
            select(ModelSelectionModel)
            .where(
                ModelSelectionModel.item_id == item_id,
                ModelSelectionModel.horizon_hours == horizon.hours,
            )
            .order_by(desc(ModelSelectionModel.selected_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _selection_model_to_record(row)


def _evaluation_model_to_record(row: ModelEvaluationModel) -> ModelEvaluationRecord:
    fold_value = row.metadata_json.get("fold_count", "0")
    try:
        fold_count = int(str(fold_value))
    except ValueError:
        fold_count = 0

    return ModelEvaluationRecord(
        id=row.id,
        item_id=row.item_id,
        horizon=ForecastHorizon(hours=row.horizon_hours),
        model_name=row.model_name,
        model_version=row.model_version,
        evaluation_window_start=row.evaluation_window_start,
        evaluation_window_end=row.evaluation_window_end,
        metric_mae=Decimal(row.metric_mae) if row.metric_mae is not None else None,
        metric_rmse=Decimal(row.metric_rmse) if row.metric_rmse is not None else None,
        metric_smape=Decimal(row.metric_smape) if row.metric_smape is not None else None,
        metric_directional_accuracy=(
            Decimal(row.metric_directional_accuracy)
            if row.metric_directional_accuracy is not None
            else None
        ),
        metric_bias=Decimal(row.metric_bias) if row.metric_bias is not None else None,
        created_at=row.created_at,
        fold_count=fold_count,
    )


def _selection_model_to_record(row: ModelSelectionModel) -> ModelSelectionRecord:
    return ModelSelectionRecord(
        id=row.id,
        item_id=row.item_id,
        horizon=ForecastHorizon(hours=row.horizon_hours),
        selected_model_name=row.selected_model_name,
        selected_model_version=row.selected_model_version,
        primary_metric=row.primary_metric,
        primary_metric_value=(
            Decimal(row.primary_metric_value) if row.primary_metric_value is not None else None
        ),
        reason=row.reason,
        selected_at=row.selected_at,
        evaluation_id=row.evaluation_id,
    )
