import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from osrs_price_forecaster.core.config import Settings
from osrs_price_forecaster.domain.entities import PriceObservation
from osrs_price_forecaster.domain.forecasting import OsrsPriceDataProvider


class MappingItemDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    examine: str | None = None
    members: bool | None = None
    lowalch: int | None = None
    highalch: int | None = None
    limit: int | None = None
    value: int | None = None


class LatestPricePointDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    high: int | None = None
    high_time: int | None = Field(default=None, alias="highTime")
    low: int | None = None
    low_time: int | None = Field(default=None, alias="lowTime")


class LatestResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: dict[str, LatestPricePointDTO]


class IntervalPricePointDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    avg_high_price: int | None = Field(default=None, alias="avgHighPrice")
    avg_low_price: int | None = Field(default=None, alias="avgLowPrice")
    high_price_volume: int | None = Field(default=None, alias="highPriceVolume")
    low_price_volume: int | None = Field(default=None, alias="lowPriceVolume")


class IntervalResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: dict[str, IntervalPricePointDTO]


class TimeseriesPointDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    timestamp: int
    avg_high_price: int | None = Field(default=None, alias="avgHighPrice")
    avg_low_price: int | None = Field(default=None, alias="avgLowPrice")
    high_price_volume: int | None = Field(default=None, alias="highPriceVolume")
    low_price_volume: int | None = Field(default=None, alias="lowPriceVolume")


class TimeseriesResponseDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[TimeseriesPointDTO]


def interval_dto_to_observation(
    *,
    item_id: int,
    interval: str,
    source_timestamp: datetime,
    dto: IntervalPricePointDTO,
    ingested_at: datetime,
) -> PriceObservation:
    mid_price: Decimal | None = None
    if dto.avg_high_price is not None and dto.avg_low_price is not None:
        mid_price = (Decimal(dto.avg_high_price) + Decimal(dto.avg_low_price)) / Decimal(2)

    return PriceObservation(
        item_id=item_id,
        interval=interval,
        source_timestamp=source_timestamp,
        ingested_at=ingested_at,
        avg_high_price=dto.avg_high_price,
        avg_low_price=dto.avg_low_price,
        high_price_volume=dto.high_price_volume,
        low_price_volume=dto.low_price_volume,
        mid_price=mid_price,
    )


@dataclass(slots=True)
class OsrsWikiClient(OsrsPriceDataProvider):
    settings: Settings
    _client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OsrsWikiClient":
        timeout = httpx.Timeout(self.settings.http_timeout_seconds)
        self._client = httpx.AsyncClient(
            base_url=str(self.settings.osrs_wiki_base_url),
            timeout=timeout,
            headers={"User-Agent": self.settings.osrs_wiki_user_agent},
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def fetch_mapping(self) -> list[dict[str, object]]:
        payload = await self._request_json("/mapping")
        if not isinstance(payload, list):
            raise ValueError("Unexpected /mapping payload type")
        parsed = [MappingItemDTO.model_validate(item) for item in payload]
        return [entry.model_dump(mode="python") for entry in parsed]

    async def fetch_latest(self) -> dict[str, object]:
        payload = await self._request_json("/latest")
        parsed = LatestResponseDTO.model_validate(payload)
        return parsed.model_dump(mode="python")

    async def fetch_interval(self, interval: str) -> dict[str, object]:
        if interval not in {"5m", "1h"}:
            raise ValueError("interval must be one of: 5m, 1h")
        payload = await self._request_json(f"/{interval}")
        parsed = IntervalResponseDTO.model_validate(payload)
        return parsed.model_dump(mode="python")

    async def fetch_timeseries(self, timestep: str, item_id: int) -> dict[str, object]:
        payload = await self._request_json(
            "/timeseries",
            params={"timestep": timestep, "id": item_id},
        )
        parsed = TimeseriesResponseDTO.model_validate(payload)
        return parsed.model_dump(mode="python")

    async def _request_json(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> object:
        if self._client is None:
            raise RuntimeError("OsrsWikiClient must be used as an async context manager")

        retries = self.settings.http_max_retries
        for attempt in range(retries + 1):
            try:
                response = await self._client.get(path, params=params)
                if response.status_code >= 400:
                    if not self._is_retryable_status(response.status_code):
                        response.raise_for_status()
                    raise httpx.HTTPStatusError(
                        "Retryable upstream status",
                        request=response.request,
                        response=response,
                    )
                return response.json()
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.HTTPStatusError,
                ValidationError,
            ):
                if attempt >= retries:
                    raise
                backoff = self.settings.http_backoff_base_seconds * (2**attempt)
                jitter = random.uniform(0.0, backoff / 2)
                await asyncio.sleep(backoff + jitter)

        raise RuntimeError("unreachable")

    @staticmethod
    def _is_retryable_status(status_code: int) -> bool:
        if status_code in {408, 429}:
            return True
        return status_code >= 500


def unix_to_utc(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)
