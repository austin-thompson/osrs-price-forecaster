from collections.abc import Sequence
from datetime import datetime

import pytest

from osrs_price_forecaster.application.ingestion.service import IngestionService
from osrs_price_forecaster.domain.entities import Item, PriceObservation


class FakeProvider:
    async def fetch_mapping(self) -> list[dict[str, object]]:
        return [{"id": 4151, "name": "Abyssal whip"}]

    async def fetch_latest(self) -> dict[str, object]:
        return {"data": {}}

    async def fetch_interval(self, interval: str) -> dict[str, object]:
        if interval not in {"5m", "1h"}:
            raise ValueError("unexpected interval")
        return {
            "data": {
                "4151": {
                    "avgHighPrice": 2_000_000,
                    "avgLowPrice": 1_990_000,
                    "highPriceVolume": 50,
                    "lowPriceVolume": 45,
                }
            }
        }

    async def fetch_timeseries(self, timestep: str, item_id: int) -> dict[str, object]:
        assert timestep in {"5m", "1h"}
        assert item_id == 4151
        return {
            "data": [
                {
                    "timestamp": 1_722_600_000,
                    "avgHighPrice": 1_995_000,
                    "avgLowPrice": 1_985_000,
                    "highPriceVolume": 30,
                    "lowPriceVolume": 28,
                },
                {
                    "timestamp": 1_722_603_600,
                    "avgHighPrice": 2_005_000,
                    "avgLowPrice": 1_995_000,
                    "highPriceVolume": 35,
                    "lowPriceVolume": 32,
                },
            ]
        }


class FakeItemRepository:
    def __init__(self) -> None:
        self.items: list[Item] = []

    async def get_item(self, item_id: int) -> Item | None:
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    async def list_items(self, limit: int = 100, offset: int = 0) -> list[Item]:
        return self.items[offset : offset + limit]

    async def upsert_items(self, items: Sequence[Item]) -> int:
        self.items = list(items)
        return len(items)


class FakePriceObservationRepository:
    def __init__(self) -> None:
        self.observations: list[PriceObservation] = []

    async def store_observations(self, observations: Sequence[PriceObservation]) -> int:
        self.observations.extend(observations)
        return len(observations)

    async def list_observations(
        self,
        item_id: int,
        interval: str,
        start_at: datetime | None,
        end_at: datetime | None,
        limit: int = 500,
    ) -> list[PriceObservation]:
        _ = (start_at, end_at)
        return [
            obs for obs in self.observations if obs.item_id == item_id and obs.interval == interval
        ][:limit]


@pytest.mark.asyncio
async def test_ingestion_service_syncs_mapping_and_prices() -> None:
    item_repo = FakeItemRepository()
    observation_repo = FakePriceObservationRepository()

    service = IngestionService(
        provider=FakeProvider(),
        item_repository=item_repo,
        observation_repository=observation_repo,
        tracked_item_ids=[4151],
    )

    await service.run_once()

    assert len(item_repo.items) == 1
    assert item_repo.items[0].item_id == 4151

    intervals = {obs.interval for obs in observation_repo.observations}
    assert intervals == {"5m", "1h"}
    assert len(observation_repo.observations) == 6
    assert all(obs.ingested_at.tzinfo is not None for obs in observation_repo.observations)
