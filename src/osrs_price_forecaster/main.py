from fastapi import FastAPI

from osrs_price_forecaster import __version__
from osrs_price_forecaster.api.routes.health import router as health_router
from osrs_price_forecaster.api.routes.v1 import router as v1_router
from osrs_price_forecaster.core.config import Settings, get_settings
from osrs_price_forecaster.core.logging import configure_logging


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="osrs-price-forecaster",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


app = create_app
