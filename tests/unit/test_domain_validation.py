from datetime import UTC, datetime
from decimal import Decimal

import pytest

from osrs_price_forecaster.domain.entities import ForecastResult, Item, SavedAnalysisPreference
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


def test_saved_analysis_preference_rejects_duplicate_filters() -> None:
    with pytest.raises(ValidationError, match="signal_labels must not contain duplicates"):
        SavedAnalysisPreference(
            id=1,
            name="Shortlist",
            horizon=ForecastHorizon(hours=1),
            signal_labels=["stable", "stable"],
            liquidity_statuses=[],
            drift_states=[],
            top_n=25,
            watchlist_id=None,
            created_at=datetime.now(UTC),
        )


def test_saved_analysis_preference_rejects_unsupported_filters() -> None:
    with pytest.raises(ValidationError, match="drift_states contains an unsupported value"):
        SavedAnalysisPreference(
            id=1,
            name="Shortlist",
            horizon=ForecastHorizon(hours=1),
            signal_labels=[],
            liquidity_statuses=[],
            drift_states=["volatile"],
            top_n=25,
            watchlist_id=None,
            created_at=datetime.now(UTC),
        )
