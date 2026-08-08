import json
from pathlib import Path

from osrs_price_forecaster.infrastructure.clients.osrs_wiki import (
    IntervalResponseDTO,
    LatestResponseDTO,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_latest_fixture_parses() -> None:
    payload = json.loads((FIXTURES_DIR / "osrs_latest_sample.json").read_text(encoding="utf-8"))
    parsed = LatestResponseDTO.model_validate(payload)
    assert parsed.data["4151"].high == 2_345_678


def test_interval_fixture_parses() -> None:
    payload = json.loads((FIXTURES_DIR / "osrs_5m_sample.json").read_text(encoding="utf-8"))
    parsed = IntervalResponseDTO.model_validate(payload)
    assert parsed.data["4151"].avg_high_price == 2_340_000
