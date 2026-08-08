# Cycle 2 — Active planning

Branch: feat/phase5-8-cycle2
Started: 2026-08-08
Status: Closed for MVP scope (2026-08-08)

## Objective

Expand the phase 5–8 MVP slices into working implementations. Replace hardcoded placeholder behavior with synthesis-backed outputs, complete the initial CRUD surfaces for watchlists, and add the first meaningful filtering and comparison capabilities.

## Gap analysis (as of 2026-08-08)

### Phase 5 — Portfolio ranking and watchlists

- Phase 5 recommendation output is now wired to the synthesis layer, so ranking and recommendation responses derive their score, signal label, and reason codes from real synthesis data rather than hardcoded values.
- Champion model metadata is now populated from the selection repository for recommendation and ranking responses.
- `GET /api/v1/rankings` and `GET /api/v1/recommendations` now support filtering by `signal_label`, `liquidity_status`, `drift_state`, and `top_n`.
- The watchlist CRUD MVP is now implemented through the persisted API surface.

### Phase 6 — Analysis workflows and explanation depth

- The single-item analysis-summary endpoint is now working against the synthesis layer.
- A new cohort comparison endpoint is available at `/api/v1/cohort-comparison` for side-by-side multi-item signal views.
- The contract boundary between `/analysis-summary`, `/summary`, `/signal`, and `/explanation` remains something to document more explicitly as the phase evolves.
- Benchmark-history views are still pending and remain a future enhancement.

### Phase 7 — Reliability and observability

- The operational summary now queries the latest `price_observations` row and derives `latest_ingested_at` from the database.
- `freshness_status` is derived from the age of the newest observation and escalates to `warning` or `stale` when freshness thresholds are crossed.
- `warnings` now includes real conditions such as `stale_ingestion` or `ingestion_delay`.
- The operational summary endpoint now provides a meaningful health signal for operators.

### Phase 8 — Personalization and saved analysis

- `GET /api/v1/watchlists/{watchlist_id}` now returns a saved watchlist by ID.
- `DELETE /api/v1/watchlists/{watchlist_id}` now removes a saved watchlist when it exists.
- The CRUD surface for the initial watchlist MVP is now in place: create, list, get, and delete are all supported.

## Order of operations

| Step | Work item                                           | Blocking      | Status    |
| ---- | --------------------------------------------------- | ------------- | --------- |
| 1    | Wire `RecommendationService` to `SynthesisService`  | Steps 3 and 5 | Completed |
| 2    | Wire Phase 7 operational summary to real DB queries | Nothing       | Completed |
| 3    | Phase 5 ranking filters + champion model population | Step 1        | Completed |
| 4    | Phase 8 watchlist fetch and delete endpoints        | Nothing       | Completed |
| 5    | Phase 6 cohort comparison endpoint                  | Steps 1 and 3 | Completed |

### Step 1 rationale

The initial hardcoded recommendation behavior was the highest-leverage blocker for the cycle. Once `RecommendationService` delegates to the synthesis layer, ranking, recommendation, and analysis surfaces can expose consistent signal data.

### Step 2 rationale

Self-contained and unblocked. Query `price_observations` for the most recent `ingested_at`, derive `freshness_status` from elapsed time against a configurable threshold, populate `warnings` with real conditions.

### Step 3 rationale

Once scores are real, filter params (`signal_label`, `liquidity_status`, `drift_state`, `top_n`) on `/api/v1/rankings` and `/api/v1/recommendations` become meaningful. This also fixes `champion_model_name` by querying the selection repository.

### Step 4 rationale

Straightforward CRUD completion. Add `GET /api/v1/watchlists/{watchlist_id}` and `DELETE /api/v1/watchlists/{watchlist_id}` using the existing repository and persistence layer.

### Step 5 rationale

Depends on real per-item scores (step 1) and benefits from the filter work (step 3). Accepts a list of item IDs and returns their current signal state side by side as a cohort view.

## Acceptance criteria for cycle 2 closure

- `GET /api/v1/rankings?horizon_hours=1` returns items with real synthesis-derived scores, real signal labels, and populated champion model fields.
- `GET /api/v1/operational-summary` returns a real `latest_ingested_at` timestamp and a `freshness_status` derived from elapsed time.
- `GET /api/v1/watchlists`, `POST /api/v1/watchlists`, `GET /api/v1/watchlists/{watchlist_id}`, and `DELETE /api/v1/watchlists/{watchlist_id}` are implemented and covered by tests.
- A cohort comparison endpoint exists and returns signal state for multiple items in a single response.
- All new behavior is covered by unit tests. No hardcoded scores or placeholder return values remain in production paths.
