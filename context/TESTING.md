# Testing Strategy

## Unit tests

Focus:

- Domain validation and invariants.
- Configuration parsing and defaults.
- Mapping and adapter logic with mocked HTTP transport.
- API handler behavior that does not require live infrastructure.

## Integration tests

Focus:

- Async SQLAlchemy repository/database behavior.
- Alembic migration viability.
- Readiness checks against PostgreSQL.

## Contract tests

Focus:

- External OSRS payload fixtures parsed by DTOs and mappers.
- Detect schema drift safely without calling live API.

## Fixture strategy

- Store deterministic JSON fixtures under tests/fixtures.
- Keep fixtures small, representative, and versioned.

## Migration tests

- Apply migrations against disposable PostgreSQL instance.
- Verify essential tables and constraints exist.

## Backtesting tests

Planned in Phase 1:

- Walk-forward splits.
- Champion selection rules.
- Forecast persistence and evaluation linkage.

## Data-leakage tests

Planned in Phase 1:

- Ensure training windows do not include target/future observations.

## Property-based tests

Possible later enhancement for parser robustness and invariants.

## Live API prohibition

Normal test runs must not depend on live OSRS API access.

## Known test dependency migration

The current FastAPI/Starlette `TestClient` emits a deprecation warning recommending the
future `httpx2` client. The project still depends on `httpx` for both application transport
and tests, and `httpx2` is not part of the locked dependency set. Migrate the API tests once
that client is deliberately adopted; until then, the warning is expected and does not affect
test results.

## Cycle 3 readiness verification (2026-08-16)

- Added a missing-forecast regression test for synthesis summary and explanation paths.
- Added a PostgreSQL integration test for persisted watchlist CRUD with isolated cleanup.
- Quality gates include Ruff formatting/linting, strict mypy over `src` and `tests`, the
  infrastructure-free test suite, and PostgreSQL integration tests in CI.

## Phase 1 Completion Evidence (2026-08-02)

Verification run summary:

- Services and migrations:
  - `docker compose up --build -d --wait`
  - `docker compose exec -T api uv run alembic upgrade head`
- Collector and forecaster execution (containerized runtime):
  - `docker compose --profile workers run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' collector`
  - `docker compose --profile future run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' forecaster`
- Quality gates:
  - `uv run ruff check src tests`
  - `uv run mypy src tests`
  - `uv run pytest -m "not integration"`

Database evidence captured from PostgreSQL:

- Ingestion reliability for tracked items (4151, 11840):
  - `price_observations` contains 5m and 1h rows per tracked item.
  - Non-null `mid_price` values are present for training/evaluation.
- Forecast persistence:
  - `forecasts` contains entries for horizons 1h, 6h, and 24h per tracked item.
- Champion model selection with rationale:
  - `model_selections` contains per-item/per-horizon selections with `primary_metric=mae` and non-empty `reason`.

Acceptance criteria mapping:

- Configurable tracked item universe ingested reliably: satisfied.
- Forecasts for 1h/6h/24h generated and persisted: satisfied.
- Champion model selected per item and horizon with stored rationale: satisfied.

## Phase 2 Verification Evidence (2026-08-02)

Verification run summary:

- Runtime rebuild and migration check:
  - `docker compose up --build -d --wait`
  - `docker compose exec -T api uv run alembic upgrade head`
- Live ingestion and forecasting runs:
  - `docker compose --profile workers run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' collector`
  - `docker compose --profile future run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' forecaster`
- Phase 2 API verification:
  - `GET /api/v1/items/4151/forecasts?horizon_hours=1&limit=1`
  - `GET /api/v1/items/4151/backtesting-report?horizon_hours=1`

Observed evidence:

- Forecast metadata includes uncertainty and drift fields:
  - `prediction_interval_confidence`
  - `prediction_interval_low`
  - `prediction_interval_high`
  - `liquidity_filter_min_volume`
  - `liquidity_observations_dropped`
  - `drift_state`
  - `drift_ratio`
- Backtesting report leaderboard includes additional model families:
  - `naive_last`
  - `rolling_mean_3`
  - `ewma_0.4`
  - `linear_trend`
  - `spread_adjusted_rm_6`
- Drift/quality summary fields are populated in leaderboard output:
  - `trend`
  - `mae_ratio_vs_previous`

Database evidence snapshot:

- `model_evaluations` contains rows for all five model families above, with recent `created_at` timestamps from this verification run.

Phase 2 scope evidence mapping:

- Prediction intervals: satisfied (forecast metadata).
- Liquidity filters: satisfied (forecast metadata + filtered run behavior).
- Richer features/additional models: satisfied (leaderboard + evaluation table).
- Drift detection: satisfied (trend + ratio fields in report).
- Backtesting reports: satisfied (`/backtesting-report` endpoint output).

## Phase 2 Benchmark Checklist

Use this checklist when deciding whether Phase 2 can be marked complete.

1. Rebuild runtime and run migrations.
2. Run collector and forecaster in containerized mode with valid User-Agent.
3. Capture benchmark metrics for tracked items and horizons (1h, 6h, 24h).
4. Compare MAE against Phase 1 baseline snapshots.
5. Verify prediction interval calibration range.
6. Verify backtesting report endpoint fields and model coverage.
7. Record results in this file under a dated evidence block.

Recommended command sequence:

- `docker compose up --build -d --wait`
- `docker compose exec -T api uv run alembic upgrade head`
- `docker compose --profile workers run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' collector`
- `docker compose --profile future run --rm -e OSRS_WIKI_USER_AGENT='osrs-price-forecaster/0.1 (contact: local-dev@example.com)' forecaster`
- `curl "http://localhost:8000/api/v1/items/4151/backtesting-report?horizon_hours=1"`

Recommended SQL checks:

- Model coverage in evaluations:
  - `SELECT model_name, model_version, COUNT(*) FROM model_evaluations GROUP BY model_name, model_version ORDER BY model_name;`
- Horizon coverage in forecasts:
  - `SELECT item_id, horizon_hours, COUNT(*) FROM forecasts GROUP BY item_id, horizon_hours ORDER BY item_id, horizon_hours;`
- Drift metadata presence in forecasts:
  - `SELECT COUNT(*) FILTER (WHERE metadata ? 'drift_state') AS with_drift, COUNT(*) AS total FROM forecasts;`

Benchmark pass/fail rubric:

- MAE comparison: pass when >= 2 item/horizon cells improve vs baseline and worst-cell regression is no worse than -2%.
- Interval readiness: pass when interval metadata fields are persisted and empirical coverage query is reproducible for realized windows.
- Report completeness: pass when backtesting endpoint returns leaderboard rows for enabled models and trend fields.

## Phase 2 Benchmark Run (2026-08-03)

Run scope:

- Runtime rebuild + migration.
- Collector and forecaster executed in containerized mode.
- API and PostgreSQL benchmark queries executed.

Observed benchmark outputs:

- Backtesting report endpoint:
  - `GET /api/v1/items/4151/backtesting-report?horizon_hours=1` returned leaderboard rows with trend fields.
  - Leaderboard included all enabled models: `naive_last`, `rolling_mean_3`, `ewma_0.4`, `linear_trend`, `spread_adjusted_rm_6`.
- Evaluation model coverage:
  - `naive_last`: 30 rows
  - `rolling_mean_3`: 30 rows
  - `ewma_0.4`: 12 rows
  - `linear_trend`: 12 rows
  - `spread_adjusted_rm_6`: 12 rows
- Forecast horizon coverage (tracked items 4151, 11840):
  - 1h/6h/24h all present for both tracked items (5 rows each at query time).
- Drift and interval metadata presence in forecasts:
  - `with_drift`: 12
  - `with_interval_bounds`: 12
  - `total_forecasts`: 30

MAE improvement vs pre-Phase-2 baseline snapshot:

- 4151 / 1h: -0.452%
- 4151 / 6h: +0.073%
- 4151 / 24h: +0.476%
- 11840 / 1h: -1.121%
- 11840 / 6h: -0.447%
- 11840 / 24h: -0.719%

Pass/fail assessment:

- Report completeness: PASS.
- Drift metadata persistence: PASS.
- Additional model family coverage: PASS.
- MAE comparison threshold (>= 2 improving cells; worst-cell regression >= -2%): PASS.
- Interval readiness threshold (metadata persistence + reproducible coverage query): PASS.

Follow-up actions after Phase 2 closure:

- Continue collecting realized-window interval coverage as additional forecast-target timestamps mature.
- Use Phase 3 user-facing surfaces to expose benchmark trend history and calibration summaries.
