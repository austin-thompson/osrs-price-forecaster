import os

import pytest
from pydantic import ValidationError

from osrs_price_forecaster.core.config import Settings


def test_settings_parses_comma_separated_lists() -> None:
    os.environ["TRACKED_ITEM_IDS"] = "[1,2,3]"
    os.environ["FORECAST_HORIZONS_HOURS"] = "[1,6,24]"
    settings = Settings()

    assert settings.tracked_item_ids == [1, 2, 3]
    assert settings.forecast_horizons_hours == [1, 6, 24]


def test_settings_accepts_ordered_operational_freshness_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPERATIONAL_FRESHNESS_WARNING_MINUTES", "15")
    monkeypatch.setenv("OPERATIONAL_FRESHNESS_STALE_MINUTES", "45")

    settings = Settings()

    assert settings.operational_freshness_warning_minutes == 15
    assert settings.operational_freshness_stale_minutes == 45


def test_settings_rejects_unordered_operational_freshness_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPERATIONAL_FRESHNESS_WARNING_MINUTES", "45")
    monkeypatch.setenv("OPERATIONAL_FRESHNESS_STALE_MINUTES", "45")

    with pytest.raises(ValidationError, match="must be less than"):
        Settings()
