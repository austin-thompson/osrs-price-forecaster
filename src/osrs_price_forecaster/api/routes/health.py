from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from osrs_price_forecaster.api.dependencies import get_db_session

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: str
    timestamp: datetime


class ReadyResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


@router.get("/live", response_model=LiveResponse, status_code=status.HTTP_200_OK)
async def live() -> LiveResponse:
    return LiveResponse(status="ok", timestamp=datetime.now(UTC))


@router.get("/ready", response_model=ReadyResponse)
async def ready(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> ReadyResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="degraded",
            database="unreachable",
            timestamp=datetime.now(UTC),
        )
    return ReadyResponse(status="ok", database="reachable", timestamp=datetime.now(UTC))
