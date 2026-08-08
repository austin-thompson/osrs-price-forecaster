from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from osrs_price_forecaster.domain.entities import (
    ForecastRequest,
    ForecastResult,
    ModelEvaluation,
    ModelSelection,
    PriceObservation,
)


class OsrsPriceDataProvider(Protocol):
    async def fetch_mapping(self) -> list[dict[str, object]]: ...

    async def fetch_latest(self) -> dict[str, object]: ...

    async def fetch_interval(self, interval: str) -> dict[str, object]: ...

    async def fetch_timeseries(self, timestep: str, item_id: int) -> dict[str, object]: ...


class FeatureGenerator(Protocol):
    def generate_features(self, observations: Sequence[PriceObservation]) -> Sequence[Decimal]: ...


class ForecastModel(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    async def train(self, observations: Sequence[PriceObservation]) -> None: ...

    async def forecast(self, request: ForecastRequest) -> ForecastResult: ...


class ModelEvaluator(Protocol):
    async def evaluate(
        self,
        model: ForecastModel,
        observations: Sequence[PriceObservation],
        horizon_hours: int,
    ) -> ModelEvaluation: ...


class ModelSelector(Protocol):
    def select(
        self,
        candidates: Sequence[ModelEvaluation],
        selected_at: datetime,
    ) -> ModelSelection: ...


class CandidateModelRegistry(Protocol):
    def list_candidates(self) -> Sequence[ForecastModel]: ...
