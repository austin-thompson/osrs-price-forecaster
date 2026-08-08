from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from osrs_price_forecaster.domain.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class ForecastHorizon:
    hours: int

    def __post_init__(self) -> None:
        if self.hours <= 0:
            raise ValidationError("Forecast horizon must be positive")

    @property
    def delta(self) -> timedelta:
        return timedelta(hours=self.hours)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValidationError("datetime must be timezone-aware")
    return dt.astimezone(UTC)
