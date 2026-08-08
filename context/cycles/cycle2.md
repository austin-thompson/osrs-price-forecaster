# Cycle 2 — Active planning

Branch: feat/phase5-8-cycle2
Started: 2026-08-08
Status: In progress

## Objective

Expand the phase 5–8 MVP slices into working implementations. Fix the hardcoded placeholder behaviour that was carried over from cycle 1, complete the incomplete CRUD surfaces, and add the first meaningful filtering and comparison capabilities.

## Gap analysis (as of 2026-08-08)

### Phase 5 — Portfolio ranking and watchlists

- `RecommendationService.list_recommendations` returns hardcoded `score=0.85` and `signal_label="stable"` for every item. It does not call `SynthesisService`. This is the root cause of incorrect data across all ranking, recommendation, and analysis surfaces.
- `champion_model_name` and `champion_model_version` are always `None` in ranking and recommendation responses; the selection repository is not queried.
- No filter query params on `GET /api/v1/rankings` — no `signal_label`, `liquidity_status`, `drift_state`, or `top_n` support.
- No `GET /api/v1/watchlist/{id}` or `DELETE /api/v1/watchlist/{id}` endpoints.

### Phase 6 — Analysis workflows and explanation depth

- Analysis-summary scores are wrong until the Phase 5 recommendation wiring is fixed (inherited dependency).
- The contract boundary between `/analysis-summary` and the `/summary`, `/signal`, `/explanation` endpoints is undocumented; risk of silent drift if either evolves independently.
- No multi-item cohort or comparison endpoint.
- No benchmark-history view showing how signal or MAE has trended over time for an item/horizon.

### Phase 7 — Reliability and observability

- `freshness_status` is hardcoded; no database query is performed.
- `latest_ingested_at` is always `None`; `price_observations` is not queried.
- `warnings` is always an empty list.
- The operational summary provides no real signal about system health.

### Phase 8 — Personalization and saved analysis

- `GET /api/v1/watchlist/{id}` is missing; a saved watchlist cannot be fetched individually.
- `DELETE /api/v1/watchlist/{id}` is missing; watchlists cannot be removed.
- CRUD surface is incomplete: create and list exist but fetch and delete do not.

## Order of operations

| Step | Work item                                           | Blocking      | Status      |
| ---- | --------------------------------------------------- | ------------- | ----------- |
| 1    | Wire `RecommendationService` to `SynthesisService`  | Steps 3 and 5 | Not started |
| 2    | Wire Phase 7 operational summary to real DB queries | Nothing       | Not started |
| 3    | Phase 5 ranking filters + champion model population | Step 1        | Not started |
| 4    | Phase 8 watchlist fetch and delete endpoints        | Nothing       | Not started |
| 5    | Phase 6 cohort comparison endpoint                  | Steps 1 and 3 | Not started |

### Step 1 rationale

Every ranking, recommendation, and analysis surface returns synthetic data until `RecommendationService` delegates to `SynthesisService.build_signal`. This is the highest-leverage fix in the cycle.

### Step 2 rationale

Self-contained and unblocked. Query `price_observations` for the most recent `ingested_at`, derive `freshness_status` from elapsed time against a configurable threshold, populate `warnings` with real conditions.

### Step 3 rationale

Once scores are real, filter params (`signal_label`, `liquidity_status`, `drift_state`, `top_n`) on `/api/v1/rankings` become meaningful. Also fixes `champion_model_name` by querying the selection repository.

### Step 4 rationale

Straightforward CRUD completion. Add `GET /api/v1/watchlist/{id}` and `DELETE /api/v1/watchlist/{id}` using the existing repository and persistence layer.

### Step 5 rationale

Depends on real per-item scores (step 1) and benefits from the filter work (step 3). Accepts a list of item IDs and returns their current signal state side by side as a cohort view.

## Acceptance criteria for cycle 2 closure

- `GET /api/v1/rankings?horizon_hours=1` returns items with real synthesis-derived scores, real signal labels, and populated champion model fields.
- `GET /api/v1/operational/summary` returns a real `latest_ingested_at` timestamp and a `freshness_status` derived from elapsed time.
- `GET /api/v1/watchlist/{id}` and `DELETE /api/v1/watchlist/{id}` exist and are covered by tests.
- A cohort comparison endpoint exists and returns signal state for multiple items in a single response.
- All new behavior is covered by unit tests. No hardcoded scores or placeholder return values remain in production paths.
