from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/osrs_price_forecaster",
        alias="DATABASE_URL",
    )

    osrs_wiki_base_url: str = Field(
        default="https://prices.runescape.wiki/api/v1/osrs",
        alias="OSRS_WIKI_BASE_URL",
    )
    osrs_wiki_user_agent: str = Field(
        default="osrs-price-forecaster/0.2.0-alpha (contact: replace-me@example.com)",
        alias="OSRS_WIKI_USER_AGENT",
    )

    http_timeout_seconds: float = Field(default=10.0, alias="HTTP_TIMEOUT_SECONDS")
    http_max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")
    http_backoff_base_seconds: float = Field(default=0.25, alias="HTTP_BACKOFF_BASE_SECONDS")

    collector_interval_seconds: int = Field(default=300, alias="COLLECTOR_INTERVAL_SECONDS")
    operational_freshness_warning_minutes: int = Field(
        default=90, gt=0, alias="OPERATIONAL_FRESHNESS_WARNING_MINUTES"
    )
    operational_freshness_stale_minutes: int = Field(
        default=180, gt=0, alias="OPERATIONAL_FRESHNESS_STALE_MINUTES"
    )
    tracked_item_ids: list[int] = Field(
        default_factory=lambda: [4151, 11840], alias="TRACKED_ITEM_IDS"
    )
    forecast_horizons_hours: list[int] = Field(
        default_factory=lambda: [1, 6, 24], alias="FORECAST_HORIZONS_HOURS"
    )

    @field_validator("tracked_item_ids", mode="before")
    @classmethod
    def parse_tracked_item_ids(cls, value: object) -> list[int]:
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [int(v) for v in value]
        raise ValueError("TRACKED_ITEM_IDS must be a list[int] or comma-separated string")

    @field_validator("forecast_horizons_hours", mode="before")
    @classmethod
    def parse_forecast_horizons(cls, value: object) -> list[int]:
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [int(v) for v in value]
        raise ValueError("FORECAST_HORIZONS_HOURS must be a list[int] or comma-separated string")

    @model_validator(mode="after")
    def validate_operational_freshness_thresholds(self) -> "Settings":
        if self.operational_freshness_warning_minutes >= self.operational_freshness_stale_minutes:
            raise ValueError(
                "OPERATIONAL_FRESHNESS_WARNING_MINUTES must be less than "
                "OPERATIONAL_FRESHNESS_STALE_MINUTES"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
