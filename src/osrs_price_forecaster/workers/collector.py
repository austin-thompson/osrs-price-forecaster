import asyncio

import structlog

from osrs_price_forecaster.application.ingestion.service import IngestionService
from osrs_price_forecaster.core.config import get_settings
from osrs_price_forecaster.core.logging import configure_logging
from osrs_price_forecaster.infrastructure.clients.osrs_wiki import OsrsWikiClient
from osrs_price_forecaster.infrastructure.database.repositories import (
    SqlAlchemyItemRepository,
    SqlAlchemyPriceObservationRepository,
)
from osrs_price_forecaster.infrastructure.database.session import async_session_factory

logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    if "replace-me@example.com" in settings.osrs_wiki_user_agent:
        logger.warning(
            "collector.user_agent_placeholder",
            component="collector",
            message="Set OSRS_WIKI_USER_AGENT before enabling live collection",
        )
        return

    async with OsrsWikiClient(settings=settings) as provider:
        async with async_session_factory() as session:
            service = IngestionService(
                provider=provider,
                item_repository=SqlAlchemyItemRepository(session),
                observation_repository=SqlAlchemyPriceObservationRepository(session),
                tracked_item_ids=settings.tracked_item_ids,
            )
            await service.run_once()

    logger.info(
        "collector.run_complete",
        component="collector",
        interval_seconds=settings.collector_interval_seconds,
        tracked_items=settings.tracked_item_ids,
    )


if __name__ == "__main__":
    asyncio.run(main())
