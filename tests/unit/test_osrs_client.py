from typing import cast

import httpx
import pytest

from osrs_price_forecaster.core.config import Settings
from osrs_price_forecaster.infrastructure.clients.osrs_wiki import OsrsWikiClient


@pytest.mark.asyncio
async def test_fetch_interval_parses_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"].startswith("osrs-price-forecaster/")
        assert request.url.path.endswith("/5m")
        return httpx.Response(
            status_code=200,
            json={
                "data": {
                    "4151": {
                        "avgHighPrice": 2_340_000,
                        "avgLowPrice": 2_330_000,
                        "highPriceVolume": 50,
                        "lowPriceVolume": 65,
                    }
                }
            },
        )

    transport = httpx.MockTransport(handler)
    settings = Settings()

    client = OsrsWikiClient(settings=settings)
    client._client = httpx.AsyncClient(
        base_url=str(settings.osrs_wiki_base_url),
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        headers={"User-Agent": settings.osrs_wiki_user_agent},
        transport=transport,
    )

    result = await client.fetch_interval("5m")
    data = cast(dict[str, object], result["data"])
    item = cast(dict[str, object], data["4151"])
    assert item["avg_high_price"] == 2_340_000

    await client._client.aclose()


@pytest.mark.asyncio
async def test_non_retryable_http_error_bubbles() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    settings = Settings()

    client = OsrsWikiClient(settings=settings)
    client._client = httpx.AsyncClient(
        base_url=str(settings.osrs_wiki_base_url),
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        headers={"User-Agent": settings.osrs_wiki_user_agent},
        transport=transport,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.fetch_latest()

    await client._client.aclose()
