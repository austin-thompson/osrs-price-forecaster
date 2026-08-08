from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from osrs_price_forecaster.domain.entities import ForecastRequest, PriceObservation
from osrs_price_forecaster.domain.value_objects import ForecastHorizon
from osrs_price_forecaster.infrastructure.forecasting.baseline_models import (
    EwmaModel,
    LinearTrendModel,
    SpreadAdjustedRollingModel,
)


def _sample_observations() -> list[PriceObservation]:
    start = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
    values: list[PriceObservation] = []
    for idx in range(10):
        high = 100 + (idx * 3)
        low = 90 + (idx * 3)
        values.append(
            PriceObservation(
                item_id=1,
                interval="1h",
                source_timestamp=start + timedelta(hours=idx),
                ingested_at=start + timedelta(hours=idx),
                avg_high_price=high,
                avg_low_price=low,
                high_price_volume=100,
                low_price_volume=120,
                mid_price=(Decimal(high) + Decimal(low)) / Decimal(2),
            )
        )
    return values


@pytest.mark.asyncio
async def test_ewma_model_forecasts_after_training() -> None:
    model = EwmaModel(alpha=Decimal("0.5"))
    observations = _sample_observations()
    await model.train(observations)

    request = ForecastRequest(
        item_id=1,
        horizon=ForecastHorizon(hours=1),
        forecast_created_at=observations[-1].source_timestamp,
    )
    result = await model.forecast(request)

    assert result.predicted_mid_price > 0
    assert result.model_name.startswith("ewma")


@pytest.mark.asyncio
async def test_linear_trend_model_forecasts_after_training() -> None:
    model = LinearTrendModel()
    observations = _sample_observations()
    await model.train(observations)

    request = ForecastRequest(
        item_id=1,
        horizon=ForecastHorizon(hours=2),
        forecast_created_at=observations[-1].source_timestamp,
    )
    result = await model.forecast(request)

    assert observations[-1].mid_price is not None
    assert result.predicted_mid_price > observations[-1].mid_price
    assert result.model_name == "linear_trend"


@pytest.mark.asyncio
async def test_spread_adjusted_model_uses_spread_feature() -> None:
    model = SpreadAdjustedRollingModel(window_size=5, spread_weight=Decimal("0.1"))
    observations = _sample_observations()
    await model.train(observations)

    request = ForecastRequest(
        item_id=1,
        horizon=ForecastHorizon(hours=1),
        forecast_created_at=observations[-1].source_timestamp,
    )
    result = await model.forecast(request)

    assert result.predicted_mid_price > 0
    assert result.metadata["strategy"] == "spread_adjusted_rolling_mean"
