from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from osrs_price_forecaster.domain.exceptions import ValidationError
from osrs_price_forecaster.domain.value_objects import ForecastHorizon, ensure_utc


@dataclass(slots=True, frozen=True)
class Item:
    item_id: int
    name: str
    tradeable: bool = True

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        if not self.name.strip():
            raise ValidationError("name must not be empty")


@dataclass(slots=True, frozen=True)
class Watchlist:
    id: int
    name: str
    item_ids: list[int]

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValidationError("id must be positive")
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if any(item_id <= 0 for item_id in self.item_ids):
            raise ValidationError("item_ids must be positive")


@dataclass(slots=True, frozen=True)
class PriceObservation:
    item_id: int
    interval: str
    source_timestamp: datetime
    ingested_at: datetime
    avg_high_price: int | None = None
    avg_low_price: int | None = None
    high_price_volume: int | None = None
    low_price_volume: int | None = None
    mid_price: Decimal | None = None

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        if not self.interval.strip():
            raise ValidationError("interval must not be empty")
        ensure_utc(self.source_timestamp)
        ensure_utc(self.ingested_at)

        for value in (self.avg_high_price, self.avg_low_price):
            if value is not None and value < 0:
                raise ValidationError("prices must be nonnegative")

        for value in (self.high_price_volume, self.low_price_volume):
            if value is not None and value < 0:
                raise ValidationError("volumes must be nonnegative")


@dataclass(slots=True, frozen=True)
class ForecastRequest:
    item_id: int
    horizon: ForecastHorizon
    forecast_created_at: datetime

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        ensure_utc(self.forecast_created_at)


@dataclass(slots=True, frozen=True)
class ForecastResult:
    item_id: int
    horizon: ForecastHorizon
    forecast_created_at: datetime
    forecast_target_at: datetime
    predicted_mid_price: Decimal
    model_name: str
    model_version: str
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        created_at = ensure_utc(self.forecast_created_at)
        target_at = ensure_utc(self.forecast_target_at)
        if target_at <= created_at:
            raise ValidationError("forecast_target_at must be after forecast_created_at")
        if self.predicted_mid_price < 0:
            raise ValidationError("predicted_mid_price must be nonnegative")
        if not self.model_name.strip():
            raise ValidationError("model_name must not be empty")
        if not self.model_version.strip():
            raise ValidationError("model_version must not be empty")


@dataclass(slots=True, frozen=True)
class ModelEvaluation:
    item_id: int
    horizon: ForecastHorizon
    model_name: str
    model_version: str
    mae: Decimal | None = None
    rmse: Decimal | None = None
    smape: Decimal | None = None
    directional_accuracy: Decimal | None = None
    bias: Decimal | None = None

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        if not self.model_name.strip() or not self.model_version.strip():
            raise ValidationError("model metadata must not be empty")


@dataclass(slots=True, frozen=True)
class ModelSelection:
    item_id: int
    horizon: ForecastHorizon
    selected_model_name: str
    selected_model_version: str
    primary_metric: str
    reason: str

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValidationError("item_id must be positive")
        if not self.selected_model_name.strip() or not self.selected_model_version.strip():
            raise ValidationError("selected model metadata must not be empty")
        if not self.primary_metric.strip() or not self.reason.strip():
            raise ValidationError("selection metadata must not be empty")


@dataclass(slots=True, frozen=True)
class ModelEvaluationRecord:
    id: int
    item_id: int
    horizon: ForecastHorizon
    model_name: str
    model_version: str
    evaluation_window_start: datetime
    evaluation_window_end: datetime
    metric_mae: Decimal | None
    metric_rmse: Decimal | None
    metric_smape: Decimal | None
    metric_directional_accuracy: Decimal | None
    metric_bias: Decimal | None
    created_at: datetime
    fold_count: int


@dataclass(slots=True, frozen=True)
class ModelSelectionRecord:
    id: int
    item_id: int
    horizon: ForecastHorizon
    selected_model_name: str
    selected_model_version: str
    primary_metric: str
    primary_metric_value: Decimal | None
    reason: str
    selected_at: datetime
    evaluation_id: int | None
