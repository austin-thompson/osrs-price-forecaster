from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from osrs_price_forecaster.domain.entities import ForecastRequest, ForecastResult, PriceObservation
from osrs_price_forecaster.domain.forecasting import ForecastModel


@dataclass(slots=True)
class NaiveLastValueModel(ForecastModel):
    _last_mid_price: Decimal | None = None

    @property
    def name(self) -> str:
        return "naive_last"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def train(self, observations: Sequence[PriceObservation]) -> None:
        valid = [obs.mid_price for obs in observations if obs.mid_price is not None]
        self._last_mid_price = valid[-1] if valid else None

    async def forecast(self, request: ForecastRequest) -> ForecastResult:
        if self._last_mid_price is None:
            raise ValueError("Model must be trained with at least one valid observation")
        return ForecastResult(
            item_id=request.item_id,
            horizon=request.horizon,
            forecast_created_at=request.forecast_created_at,
            forecast_target_at=request.forecast_created_at + request.horizon.delta,
            predicted_mid_price=self._last_mid_price,
            model_name=self.name,
            model_version=self.version,
            metadata={"strategy": "last_observed_mid_price"},
        )


@dataclass(slots=True)
class RollingMeanModel(ForecastModel):
    window_size: int = 3
    _training_values: list[Decimal] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"rolling_mean_{self.window_size}"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def train(self, observations: Sequence[PriceObservation]) -> None:
        values = [obs.mid_price for obs in observations if obs.mid_price is not None]
        if not values:
            self._training_values = []
            return
        self._training_values = values[-self.window_size :]

    async def forecast(self, request: ForecastRequest) -> ForecastResult:
        if not self._training_values:
            raise ValueError("Model must be trained with at least one valid observation")

        predicted = sum(self._training_values) / Decimal(len(self._training_values))
        return ForecastResult(
            item_id=request.item_id,
            horizon=request.horizon,
            forecast_created_at=request.forecast_created_at,
            forecast_target_at=request.forecast_created_at + timedelta(hours=request.horizon.hours),
            predicted_mid_price=predicted,
            model_name=self.name,
            model_version=self.version,
            metadata={"strategy": f"mean_of_last_{len(self._training_values)}"},
        )


@dataclass(slots=True)
class EwmaModel(ForecastModel):
    alpha: Decimal = Decimal("0.4")
    _ewma_value: Decimal | None = None

    @property
    def name(self) -> str:
        return f"ewma_{self.alpha!s}"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def train(self, observations: Sequence[PriceObservation]) -> None:
        values = [obs.mid_price for obs in observations if obs.mid_price is not None]
        if not values:
            self._ewma_value = None
            return

        ewma = values[0]
        for value in values[1:]:
            ewma = (self.alpha * value) + ((Decimal("1") - self.alpha) * ewma)
        self._ewma_value = ewma

    async def forecast(self, request: ForecastRequest) -> ForecastResult:
        if self._ewma_value is None:
            raise ValueError("Model must be trained with at least one valid observation")

        return ForecastResult(
            item_id=request.item_id,
            horizon=request.horizon,
            forecast_created_at=request.forecast_created_at,
            forecast_target_at=request.forecast_created_at + request.horizon.delta,
            predicted_mid_price=self._ewma_value,
            model_name=self.name,
            model_version=self.version,
            metadata={"strategy": "ewma"},
        )


@dataclass(slots=True)
class LinearTrendModel(ForecastModel):
    _intercept: Decimal | None = None
    _slope: Decimal = Decimal("0")
    _count: int = 0

    @property
    def name(self) -> str:
        return "linear_trend"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def train(self, observations: Sequence[PriceObservation]) -> None:
        values = [obs.mid_price for obs in observations if obs.mid_price is not None]
        if len(values) < 2:
            self._intercept = values[0] if values else None
            self._slope = Decimal("0")
            self._count = len(values)
            return

        x_values = [Decimal(i) for i in range(len(values))]
        n = Decimal(len(values))
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values, strict=True))
        denominator = sum((x - x_mean) * (x - x_mean) for x in x_values)
        slope = Decimal("0") if denominator == 0 else numerator / denominator

        self._slope = slope
        self._intercept = y_mean - (slope * x_mean)
        self._count = len(values)

    async def forecast(self, request: ForecastRequest) -> ForecastResult:
        if self._intercept is None:
            raise ValueError("Model must be trained with at least one valid observation")

        future_index = Decimal(self._count - 1 + request.horizon.hours)
        predicted = self._intercept + (self._slope * future_index)
        return ForecastResult(
            item_id=request.item_id,
            horizon=request.horizon,
            forecast_created_at=request.forecast_created_at,
            forecast_target_at=request.forecast_created_at + request.horizon.delta,
            predicted_mid_price=predicted,
            model_name=self.name,
            model_version=self.version,
            metadata={"strategy": "linear_trend"},
        )


@dataclass(slots=True)
class SpreadAdjustedRollingModel(ForecastModel):
    window_size: int = 6
    spread_weight: Decimal = Decimal("0.2")
    _base_mid: Decimal | None = None
    _avg_spread: Decimal = Decimal("0")

    @property
    def name(self) -> str:
        return f"spread_adjusted_rm_{self.window_size}"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def train(self, observations: Sequence[PriceObservation]) -> None:
        recent = [obs for obs in observations if obs.mid_price is not None][-self.window_size :]
        if not recent:
            self._base_mid = None
            self._avg_spread = Decimal("0")
            return

        mids = [obs.mid_price for obs in recent if obs.mid_price is not None]
        self._base_mid = sum(mids) / Decimal(len(mids))

        spreads: list[Decimal] = []
        for obs in recent:
            if obs.avg_high_price is None or obs.avg_low_price is None:
                continue
            spreads.append(Decimal(obs.avg_high_price - obs.avg_low_price))
        self._avg_spread = sum(spreads) / Decimal(len(spreads)) if spreads else Decimal("0")

    async def forecast(self, request: ForecastRequest) -> ForecastResult:
        if self._base_mid is None:
            raise ValueError("Model must be trained with at least one valid observation")

        adjustment = self._avg_spread * self.spread_weight
        predicted = self._base_mid + adjustment
        return ForecastResult(
            item_id=request.item_id,
            horizon=request.horizon,
            forecast_created_at=request.forecast_created_at,
            forecast_target_at=request.forecast_created_at + request.horizon.delta,
            predicted_mid_price=predicted,
            model_name=self.name,
            model_version=self.version,
            metadata={"strategy": "spread_adjusted_rolling_mean"},
        )
