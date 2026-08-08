import asyncio

import structlog

from osrs_price_forecaster.application.forecasting.service import ForecastingService
from osrs_price_forecaster.core.config import get_settings
from osrs_price_forecaster.core.logging import configure_logging
from osrs_price_forecaster.infrastructure.database.repositories import (
    SqlAlchemyForecastRepository,
    SqlAlchemyModelEvaluationRepository,
    SqlAlchemyModelSelectionRepository,
    SqlAlchemyPriceObservationRepository,
)
from osrs_price_forecaster.infrastructure.database.session import async_session_factory
from osrs_price_forecaster.infrastructure.forecasting.baseline_models import (
    EwmaModel,
    LinearTrendModel,
    NaiveLastValueModel,
    RollingMeanModel,
    SpreadAdjustedRollingModel,
)
from osrs_price_forecaster.infrastructure.forecasting.registry import InMemoryCandidateModelRegistry

logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    registry = InMemoryCandidateModelRegistry(
        _models=[
            NaiveLastValueModel(),
            RollingMeanModel(window_size=3),
            EwmaModel(),
            LinearTrendModel(),
            SpreadAdjustedRollingModel(window_size=6),
        ]
    )

    async with async_session_factory() as session:
        service = ForecastingService(
            registry=registry,
            price_repository=SqlAlchemyPriceObservationRepository(session),
            forecast_repository=SqlAlchemyForecastRepository(session),
            evaluation_repository=SqlAlchemyModelEvaluationRepository(session),
            selection_repository=SqlAlchemyModelSelectionRepository(session),
            tracked_item_ids=settings.tracked_item_ids,
            forecast_horizons_hours=settings.forecast_horizons_hours,
            minimum_training_observations=24,
            minimum_liquidity_volume=10,
        )
        await service.run_once()

    logger.info(
        "forecaster.run_complete",
        component="forecaster",
        forecast_horizons=settings.forecast_horizons_hours,
        tracked_items=settings.tracked_item_ids,
    )


if __name__ == "__main__":
    asyncio.run(main())
