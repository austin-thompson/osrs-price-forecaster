from dataclasses import dataclass
from datetime import UTC, datetime

from osrs_price_forecaster.domain.entities import Item, PriceObservation
from osrs_price_forecaster.domain.forecasting import OsrsPriceDataProvider
from osrs_price_forecaster.domain.repositories import ItemRepository, PriceObservationRepository
from osrs_price_forecaster.infrastructure.clients.osrs_wiki import (
    IntervalPricePointDTO,
    TimeseriesPointDTO,
    interval_dto_to_observation,
    unix_to_utc,
)


@dataclass(slots=True)
class IngestionService:
    """Phase 1 ingestion orchestrator."""

    provider: OsrsPriceDataProvider
    item_repository: ItemRepository
    observation_repository: PriceObservationRepository
    tracked_item_ids: list[int]

    async def run_once(self) -> None:
        await self._sync_mapping()
        await self._ingest_interval_snapshot("5m")
        await self._ingest_interval_snapshot("1h")
        await self._backfill_timeseries("5m")
        await self._backfill_timeseries("1h")

    async def _sync_mapping(self) -> None:
        raw_items = await self.provider.fetch_mapping()
        items: list[Item] = []
        for raw_item in raw_items:
            if "id" not in raw_item or "name" not in raw_item:
                continue
            raw_id = raw_item["id"]
            raw_name = raw_item["name"]
            if not isinstance(raw_id, int | str):
                continue
            if not isinstance(raw_name, str):
                continue

            item_id = int(raw_id)
            name = raw_name
            if not name.strip() or item_id <= 0:
                continue
            items.append(
                Item(
                    item_id=item_id,
                    name=name,
                    tradeable=True,
                )
            )

        await self.item_repository.upsert_items(items)

    async def _ingest_interval_snapshot(self, interval: str) -> None:
        payload = await self.provider.fetch_interval(interval)
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return

        ingested_at = datetime.now(UTC)
        source_timestamp = ingested_at
        observations: list[PriceObservation] = []
        for item_id in self.tracked_item_ids:
            point = data.get(str(item_id))
            if not isinstance(point, dict):
                continue
            dto = IntervalPricePointDTO.model_validate(point)
            observations.append(
                interval_dto_to_observation(
                    item_id=item_id,
                    interval=interval,
                    source_timestamp=source_timestamp,
                    dto=dto,
                    ingested_at=ingested_at,
                )
            )

        await self.observation_repository.store_observations(observations)

    async def _backfill_timeseries(self, interval: str) -> None:
        ingested_at = datetime.now(UTC)
        observations: list[PriceObservation] = []

        for item_id in self.tracked_item_ids:
            payload = await self.provider.fetch_timeseries(interval, item_id)
            points = payload.get("data", [])
            if not isinstance(points, list):
                continue

            for raw_point in points:
                if not isinstance(raw_point, dict):
                    continue
                dto = TimeseriesPointDTO.model_validate(raw_point)
                source_timestamp = unix_to_utc(dto.timestamp)
                observations.append(
                    interval_dto_to_observation(
                        item_id=item_id,
                        interval=interval,
                        source_timestamp=source_timestamp,
                        dto=IntervalPricePointDTO(
                            avgHighPrice=dto.avg_high_price,
                            avgLowPrice=dto.avg_low_price,
                            highPriceVolume=dto.high_price_volume,
                            lowPriceVolume=dto.low_price_volume,
                        ),
                        ingested_at=ingested_at,
                    )
                )

        await self.observation_repository.store_observations(observations)
