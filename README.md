# osrs-price-forecaster

Local-first Old School RuneScape Grand Exchange price tracking and forecasting foundation.

Current phase: Phase 5-8 MVP slices in place (ranking, analysis summaries, operational visibility, and watchlists).

## Architecture overview

- Modular monolith with explicit boundaries.
- Shared domain/application code used by API and workers.
- Async PostgreSQL access with SQLAlchemy 2.x and asyncpg.
- External OSRS Wiki integration through typed adapter contracts.

See full architecture source of truth in context/README.md.

## Repository map

- context/: product, architecture, roadmap, data model, ADRs.
- src/osrs_price_forecaster/: API, domain, application, infrastructure, workers.
- migrations/: Alembic migration assets.
- tests/: unit, integration, contract, and fixtures.

## Local setup

1. Install uv.
2. Install dependencies:
   make install
3. Copy environment template if desired:
   cp .env.example .env
4. Start the local API and database workflow:
   bash scripts/start_local_env.sh
5. Stop the local workflow when finished:
   bash scripts/stop_local_env.sh
6. Run a broader live verification pass when needed:
   bash scripts/live_verification.sh

## Common commands

- make format
- make lint
- make typecheck
- make test
- make test-integration
- make run-api
- make run-collector
- make run-forecaster

## Completed foundation (Phase 0)

- FastAPI app factory
- /health/live and /health/ready
- Async database session wiring
- Initial schema and migration
- OSRS API client interface and skeletal adapter
- Forecasting interfaces and model registry skeleton
- Worker entrypoint skeletons

Phase 0 verification completed on 2026-08-01 against roadmap acceptance criteria.

## Completed MVP scope (Phase 1)

- Item mapping sync
- 5m/1h ingestion and timeseries backfill
- Baseline forecasting and walk-forward evaluation
- Per-item/per-horizon champion selection
- Forecast and model-performance endpoints

Phase 1 verification completed on 2026-08-02 against roadmap acceptance criteria.

## Completed Phase 2 scope

- Liquidity filtering in forecasting workflow (minimum volume threshold).
- Prediction-interval metadata persisted with forecasts.
- Additional candidate models: EWMA, linear trend, spread-adjusted rolling model.
- Drift signal classification from evaluation-history MAE ratios.
- Backtesting report API endpoint:
  - GET /api/v1/items/{item_id}/backtesting-report?horizon_hours=...

Runtime verification evidence for these capabilities is documented in context/TESTING.md under "Phase 2 Verification Evidence (2026-08-02)".
Phase 2 benchmark run and closure evidence are documented in context/TESTING.md under "Phase 2 Benchmark Run (2026-08-03)".

## Completed Phase 5-8 MVP slices

The project now includes the first analyst-facing MVP slices for the later roadmap phases:

- Phase 5: ranking and recommendation endpoints now expose synthesis-backed scores, signal labels, reason codes, and champion-model metadata, with filters for signal, liquidity, drift, and top-N selection.
- Phase 6: analysis-summary and cohort-comparison endpoints surface current signal state, supporting evidence, and side-by-side multi-item comparisons.
- Phase 7: the operational-summary endpoint now reports service health, freshness status, warnings, and the latest ingested observation timestamp from persisted price data.
- Phase 8: watchlists can be created and listed through persisted endpoints for simple saved-item workflows.

## Remaining work in the Phase 5-8 MVP implementation

These slices remain intentionally narrow, but the core analyst-facing contract is now in place:

- Phase 5: continue expanding portfolio-style ranking behavior and richer watchlist workflows.
- Phase 6: add deeper comparison and benchmark-history context where it improves analyst workflows.
- Phase 7: keep observability coverage aligned with ingestion health as the data pipeline evolves.
- Phase 8: add fetch/delete support for watchlists plus saved filters, horizon preferences, and local annotations while keeping the experience single-user and local-first.

## Contribution guidelines

When making changes, follow these expectations to keep the repository consistent:

- Read the relevant context documents before modifying behavior or architecture, especially [context/README.md](context/README.md), [context/ARCHITECTURE.md](context/ARCHITECTURE.md), [context/PRODUCT.md](context/PRODUCT.md), [context/FORECASTING.md](context/FORECASTING.md), [context/API_DESIGN.md](context/API_DESIGN.md), and the ADRs in [context/adr/README.md](context/adr/README.md) when the change affects those areas.
- Update the relevant context document or ADR whenever an architectural decision, API contract, data model, or workflow changes.
- Preserve the existing domain boundaries and avoid changing forecast semantics or storage assumptions without updating the supporting documentation.
- Add or update tests for behavior changes, especially when modifying forecasting, ingestion, synthesis, or API behavior.
- Keep commit messages concise and descriptive. The repository’s recent history uses a conventional style such as "feat: initial commit"; follow that pattern with a short imperative subject. Approved prefixes for this repository are:
  - feat: new user-facing or product functionality
  - fix: bug fixes and corrective changes
  - refactor: internal restructuring without behavior change
  - test: test additions or updates
  - docs: documentation-only changes
  - chore: maintenance, tooling, or non-functional updates
    Examples: "feat: add recommendation endpoint", "fix: correct freshness status calculation", or "docs: update contribution guidelines".
- For milestone or preview releases, tag only after a squash-merge into main. Use a semver-style tag and create a matching GitHub Release immediately after:
  ```bash
  git tag v0.x.0-alpha
  git push origin v0.x.0-alpha
  gh release create v0.x.0-alpha --title "v0.x.0-alpha" --notes "Brief description of what this cycle delivered."
  ```
  Do not tag feature branches or intermediate commits on main.

## Data-source attribution

This project consumes data from the OSRS Wiki Prices API.

## Disclaimer

This project is not affiliated with Jagex, RuneLite, or the OSRS Wiki.
Forecast outputs are experimental and are not guaranteed profit signals.
