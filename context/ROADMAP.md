# Roadmap

## Phase 0: Architecture and repository foundation

Status: Completed (verified 2026-08-01).

Objective:
Create a coherent executable skeleton with explicit boundaries.

Scope:
Documentation, project structure, health endpoints, async database wiring, migration baseline, OSRS adapter skeleton, forecasting interfaces, worker entrypoints, and CI/tooling.

Deliverables:

- Complete context docs and ADRs.
- FastAPI liveness/readiness endpoints.
- SQLAlchemy async session and initial migration.
- OSRS client and forecasting interfaces.
- Docker, compose, and quality tooling.

Acceptance criteria:

- docker compose up --build starts postgres and api.
- Liveness/readiness work.
- Alembic applies initial migration.
- Lint, typecheck, and tests pass.

Non-goals:
No production ingestion, no production forecasting, no frontend, no auth.

Major risks:

- Documentation drift.
- Boundary violations in early code.

Exit conditions:

- Repository validates architecture and developer workflow reliably.

## Phase 1: MVP data and baseline forecasting

Status: Completed (verified 2026-08-02).

Objective:
Deliver local end-to-end ingestion, baseline forecasts, and evaluation.

Scope:

- Mapping sync + 5m/1h data collection.
- Idempotent persistence and backfill.
- Baseline models, walk-forward evaluation, model selection.
- Forecast and model-performance APIs.

Deliverables:
As listed in product roadmap requirements.

Acceptance criteria:

- Configurable tracked item universe ingested reliably.
- Forecasts for 1h/6h/24h generated and persisted.
- Champion model selected per item and horizon with stored rationale.

Non-goals:
No guaranteed-profit claims, no distributed infra, no deep learning.

Major risks:

- Poor data quality for low-liquidity items.
- Data leakage in evaluation.

Exit conditions:

- Demonstrable reproducible baseline quality reports.

## Phase 2: Forecast quality and market intelligence

Status: Completed (verified 2026-08-03).

Objective:
Improve uncertainty handling, quality, and market context.

Scope:
Prediction intervals, liquidity filters, richer features, additional models, drift detection, and backtesting reports.

Deliverables:
Calibrated uncertainty outputs and model leaderboard insights.

Acceptance criteria:

- Benchmark set is documented and reproducible from local commands.
- Out-of-sample MAE comparison is reported against the Phase 1 baseline across tracked item/horizon cells, with at least 2 improving cells and worst-cell regression no worse than -2%.
- Prediction-interval readiness is demonstrated via persisted interval metadata fields and a reproducible empirical-coverage query for realized benchmark windows.
- Backtesting report endpoint returns leaderboard rows and trend fields for all enabled candidate models.
- Drift signals (`improved`, `stable`, `worsened`) are computed and persisted in forecast metadata and selection rationale.

Non-goals:
No large-scale distributed serving.

Major risks:
Increased complexity without measurable benefit.

Exit conditions:

- Additional model families justify maintenance cost.

## Phase 3: Synthesis layer

Status: Completed (verified 2026-08-08).

Objective:
Turn raw forecasts, evaluation artifacts, and market context into analyst-facing summaries that are easier to consume than raw rows.

Implementation plan:

1. Build a synthesis service that combines the latest forecast, latest evaluation metrics, drift status, liquidity context, and recency into one compact view per item/horizon.
2. Add repository helpers that fetch the latest forecast row, the latest champion model evaluation, and the most recent liquidity/coverage indicators for a given item.
3. Expose three Phase 3 endpoints:
   - GET /api/v1/items/{item_id}/summary for a compact item state snapshot.
   - GET /api/v1/items/{item_id}/signal for a recommendation-style signal label and score.
   - GET /api/v1/items/{item_id}/explanation for the evidence bundle behind the signal.
4. Keep the first implementation read-only and derived from existing data; do not introduce a new persistence layer until the synthesis contract is stable.
5. Add unit and integration tests that lock down the synthesis rules and the endpoint payloads.

Scope:
Curated item summaries, market-state snapshots, synthetic signal bundles, and explainability views that combine forecast, liquidity, drift, and model-performance evidence into a single consumable shape.

Deliverables:
A synthesized read model for each tracked item and horizon, plus API endpoints that expose that model in a stable contract.

Acceptance criteria:
A client can request one summary endpoint and receive a compact view of current forecast state, confidence, liquidity health, drift, recency, and champion-model rationale. A signal endpoint returns a simple label such as stable/caution/avoid and a reason code list. An explanation endpoint returns the evidence used to derive that label.

Non-goals:
No public-facing UI, no autonomous trading decisions, no multi-tenant operations.

Major risks:
Over-abstracting the data model before the signal semantics are stable.

Exit conditions:
The backend exposes a clear synthesis contract that downstream phases can build on without re-deriving the same evidence.

## Phase 4: Decision signals and recommendation layer

Status: Completed (verified 2026-08-08).

Objective:
Convert synthesized evidence into actionable signals such as stable, caution, or avoid, with guardrails and reason codes.

Implementation plan:

1. Expose a recommendation endpoint that returns ranked items for a requested horizon using the Phase 3 synthesis contract.
2. Add a lightweight recommendation service that assembles a signal label, score, guardrail status, and reason codes for each item.
3. Keep the first implementation read-only and derived from existing data until the ranking heuristics are validated.

Scope:
Confidence gating, freshness checks, minimum-liquidity rules, risk-adjusted scoring, and evidence-backed recommendation payloads.

Deliverables:
Recommendation endpoints and signal payloads that explain why each item is prioritized or deprioritized.

Acceptance criteria:
Each recommendation includes its scoring basis, guardrail status, and supporting evidence references.

Non-goals:
No guaranteed-profit claims and no automated execution.

Major risks:
Signals become too opaque or too brittle without clear governance.

Exit conditions:
The platform can communicate a practical next action for each tracked item.

## Phase 5: Portfolio ranking and watchlists

Status: MVP slice implemented (2026-08-08); broader ranking scope remains open.

Objective:
Move from single-item interpretation to ranked, comparable outputs across the tracked universe.

Implemented in the current MVP slice:

- Added a ranking endpoint that returns a ranked list of items for a requested horizon.
- Added a lightweight ranking service that uses the existing synthesis and recommendation contract.
- Added tests that lock down the endpoint payload and ordering behavior.

Remaining beyond the current slice:

- Watchlist-oriented persistence and saved views.
- Additional ranking filters such as liquidity, volatility, and drift thresholds.
- Broader portfolio-style ranking heuristics and top-N workflows.

Scope:
Cross-item ranking, watchlists, horizon-based prioritization, and top-N opportunity views with filters for liquidity, confidence, volatility, and drift.

Deliverables:
Ranking APIs and watchlist-oriented views for analysts and downstream consumers.

Acceptance criteria:
A caller can retrieve a ranked list of items for a given horizon and understand why each item ranks where it does.

Non-goals:
No portfolio optimization engine and no financial advice.

Major risks:
Ranking heuristics drift without clear evaluation criteria.

Exit conditions:
The system can surface the most actionable opportunities from the tracked universe in a consistent order.

## Phase 6: Analysis workflows and explanation depth

Status: MVP slice implemented (2026-08-08); broader analysis workflow scope remains open.

Objective:
Make the platform more usable as an analyst tool by improving how summaries, comparisons, and evidence are surfaced.

Implemented in the current MVP slice:

- Added an analysis-summary endpoint that aggregates the key signal, score, and evidence details for a single item/horizon.
- Added tests that lock down the summary payload and the underlying synthesis contract expectations.

Remaining beyond the current slice:

- Cohort and comparison views across multiple items.
- Benchmark history and richer historical explanation narratives.
- More detailed drill-downs into liquidity, drift, and model-selection evidence.

Scope:
Richer item summaries, cohort comparisons, benchmark history, and explanation narratives for signals, drift, liquidity, and model selection.

Deliverables:
Comparison endpoints, benchmark-history views, and improved synthesis explanations for downstream consumers.

Acceptance criteria:
A user can inspect an item or cohort and quickly understand its current signal, recent performance, and supporting evidence.

Non-goals:
No public-facing UI and no autonomous decision-making.

Major risks:
Feature work becomes too broad if it drifts into UI polish or speculative analytics before the core contract is stable.

Exit conditions:
The backend provides a practical analysis workflow that is easy to reason about and consume.

## Phase 7: Reliability and observability

Status: MVP slice implemented (2026-08-08); broader operational scope remains open.

Objective:
Make the system dependable enough for repeated use and monitoring.

Implemented in the current MVP slice:

- Added an operational-summary endpoint that exposes a simple service health view.
- Added a minimal operational service shape for future freshness and warning integrations.
- Added tests that lock down the endpoint contract for the initial slice.

Remaining beyond the current slice:

- Real ingestion-freshness checks based on persisted observation timestamps.
- Data-quality warning logic for stale or missing ingestion windows.
- Operational alerting hooks and richer health decomposition.

Scope:
Ingestion health reporting, forecast freshness monitoring, data-quality warnings, and basic operational alerting hooks.

Deliverables:
Operational reporting surfaces and monitoring hooks for stale data, weak signals, or broken ingestion paths.

Acceptance criteria:
Operators can quickly identify when data freshness, ingestion, or forecast quality has degraded.

Non-goals:
No large-scale hosted deployment and no complex enterprise monitoring stack.

Major risks:
Operational work can expand beyond the MVP if it is not kept tightly scoped.

Exit conditions:
The backend can be operated with predictable visibility and simple recovery steps.

## Phase 8: Personalization and saved analysis

Status: MVP slice implemented (2026-08-08); broader personalization scope remains open.

Objective:
Let users preserve their own analytical context without turning the project into a full application platform.

Implemented in the current MVP slice:

- Added watchlist creation and listing endpoints.
- Added persistence for a saved watchlist name and its item-id list.
- Added tests that lock down the initial create/list contract.

Remaining beyond the current slice:

- Saved filters and horizon preferences.
- Local-first annotations or notes.
- A richer personalization experience that is still scoped to a single-user workflow.

Scope:
Saved watchlists, saved filters and horizon preferences, and optional local-first annotations or notes.

Deliverables:
Persistence for user preferences and watchlist state.

Acceptance criteria:
A user can save a preferred analysis setup and return to it later without reconfiguring everything.

Non-goals:
No multi-user account system and no social or collaborative features.

Major risks:
Personalization features can create avoidable complexity before the core MVP is complete.

Exit conditions:
The product supports repeatable analyst workflows with minimal setup overhead.

## Scope guardrail for future phase planning

Additional phase design should remain tightly scoped to the core user value of transparent, local-first forecasting and analysis. If a proposal would expand the product into UI polish, autonomous trading, multi-user collaboration, or broad operational platform work before the core value is fully validated, the roadmap should call that out explicitly and keep the proposal deferred.
