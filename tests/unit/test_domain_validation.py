from datetime import UTC, datetime
from decimal import Decimal

import pytest

from osrs_price_forecaster.domain.entities import ForecastResult, Item
from osrs_price_forecaster.domain.exceptions import ValidationError
from osrs_price_forecaster.domain.value_objects import ForecastHorizon


def test_item_validation_rejects_non_positive_id() -> None:
    with pytest.raises(ValidationError):
        Item(item_id=0, name="Invalid")


def test_forecast_horizon_rejects_non_positive() -> None:
    with pytest.raises(ValidationError):
        ForecastHorizon(hours=0)


def test_forecast_result_requires_target_after_created() -> None:
    created_at = datetime.now(UTC)
    with pytest.raises(ValidationError):
        ForecastResult(
            item_id=4151,
            horizon=ForecastHorizon(hours=1),
            forecast_created_at=created_at,
            forecast_target_at=created_at,
            predicted_mid_price=Decimal("100.0"),
            model_name="naive",
            model_version="0.1",
        )
