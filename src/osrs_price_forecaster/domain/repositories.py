from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from osrs_price_forecaster.domain.entities import (
    ForecastResult,
    Item,
    ModelEvaluationRecord,
    ModelSelectionRecord,
    PriceObservation,
    Watchlist,
)
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


class ItemRepository(Protocol):
    async def get_item(self, item_id: int) -> Item | None: ...

    async def list_items(self, limit: int = 100, offset: int = 0) -> list[Item]: ...

    async def upsert_items(self, items: Sequence[Item]) -> int: ...


class SavedWatchlistRepository(Protocol):
    async def list_watchlists(self) -> list[Watchlist]: ...

    async def create_watchlist(self, *, name: str, item_ids: list[int]) -> Watchlist: ...

    async def get_watchlist(self, watchlist_id: int) -> Watchlist | None: ...

    async def delete_watchlist(self, watchlist_id: int) -> bool: ...


class PriceObservationRepository(Protocol):
    async def store_observations(self, observations: Sequence[PriceObservation]) -> int: ...

    async def list_observations(
        self,
        item_id: int,
        interval: str,
        start_at: datetime | None,
        end_at: datetime | None,
        limit: int = 500,
    ) -> list[PriceObservation]: ...


class ForecastRepository(Protocol):
    async def store_forecast(self, forecast: ForecastResult) -> int: ...

    async def list_forecasts(
        self,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ForecastResult]: ...


class ModelEvaluationRepository(Protocol):
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
    ) -> ModelEvaluationRecord: ...

    async def list_evaluations(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
        limit: int = 100,
    ) -> list[ModelEvaluationRecord]: ...


class ModelSelectionRepository(Protocol):
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
    ) -> ModelSelectionRecord: ...

    async def latest_selection(
        self,
        *,
        item_id: int,
        horizon: ForecastHorizon,
    ) -> ModelSelectionRecord | None: ...
