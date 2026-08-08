# Cycle 1 — Delivery record

Branch: main
Closed: 2026-08-08

## What cycle 1 delivered

### Phase 0 — Architecture and repository foundation

Completed: 2026-08-01

- FastAPI app factory, liveness and readiness endpoints.
- SQLAlchemy async session wiring and initial Alembic migration.
- OSRS Wiki client interface and skeletal adapter.
- Forecasting interfaces and model registry skeleton.
- Worker entrypoint skeletons.
- Docker Compose local stack, ruff, mypy, pytest tooling.

### Phase 1 — MVP data and baseline forecasting

Completed: 2026-08-02

- Item mapping sync from OSRS Wiki.
- 5m and 1h ingestion with idempotent persistence and timeseries backfill.
- Baseline models (naive, rolling mean), walk-forward evaluation, per-item/per-horizon champion selection.
- `/api/v1/items`, `/api/v1/items/{item_id}/forecasts`, `/api/v1/items/{item_id}/model-performance` endpoints.

### Phase 2 — Forecast quality and market intelligence

Completed: 2026-08-03

- Liquidity filtering before model evaluation (minimum volume threshold).
- Prediction-interval metadata persisted with forecasts.
- Additional candidate models: EWMA, linear trend, spread-adjusted rolling.
- Drift signal classification from evaluation-history MAE ratios.
- `/api/v1/items/{item_id}/backtesting-report` endpoint.

### Phase 3 — Synthesis layer

Completed: 2026-08-08

- `SynthesisService` combining latest forecast, evaluation metrics, drift state, liquidity, and recency into a single view per item/horizon.
- `/api/v1/items/{item_id}/summary`, `/signal`, `/explanation` endpoints.

### Phase 4 — Decision signals and recommendation layer

Completed: 2026-08-08

- `RecommendationService` skeleton with signal label, score, reason codes, and guardrail status.
- `/api/v1/recommendations` endpoint.

### Phase 5–8 — MVP slices

Implemented: 2026-08-08

- Phase 5: `/api/v1/rankings` endpoint returning a ranked list of items for a horizon.
- Phase 6: `/api/v1/items/{item_id}/analysis-summary` endpoint aggregating signal and evidence.
- Phase 7: `/api/v1/operational-summary` endpoint exposing a basic service-health shape.
- Phase 8: `/api/v1/watchlists` create and list endpoints backed by a `saved_watchlists` table.

## Verification evidence

See TESTING.md for phase-by-phase verification runs, database evidence, and benchmark results.

## Known limitations carried into cycle 2

- `RecommendationService` returns hardcoded scores and signal labels; it does not delegate to `SynthesisService`.
- Phase 7 operational summary fields (`freshness_status`, `latest_ingested_at`, `warnings`) are all placeholders.
- Phase 8 watchlist CRUD is incomplete — fetch and delete endpoints are missing.
- Phase 5 ranking filters do not exist yet; `champion_model_name` is always `None` in ranking/recommendation responses.

These are tracked as the starting gaps for cycle 2.
