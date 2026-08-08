import os

from osrs_price_forecaster.core.config import Settings


def test_settings_parses_comma_separated_lists() -> None:
    os.environ["TRACKED_ITEM_IDS"] = "[1,2,3]"
    os.environ["FORECAST_HORIZONS_HOURS"] = "[1,6,24]"
    settings = Settings()

    assert settings.tracked_item_ids == [1, 2, 3]
    assert settings.forecast_horizons_hours == [1, 6, 24]
