# API Design (Phase 1 Plan)

## Versioning

- Base path: /api/v1
- Additive changes preferred.
- Breaking changes require new major API version.

## Planned routes

Health (Phase 0 implementation):

- GET /health/live
- GET /health/ready

Domain routes (Phase 1):

- GET /api/v1/items
- GET /api/v1/items/{item_id}
- GET /api/v1/items/{item_id}/prices
- GET /api/v1/items/{item_id}/forecasts
- GET /api/v1/items/{item_id}/model-performance
- GET /api/v1/ingestion/status

Phase 2 analytics route:

- GET /api/v1/items/{item_id}/backtesting-report

Phase 3 synthesis routes:

- GET /api/v1/items/{item_id}/summary
  - Returns a compact item-state summary for the default horizon set.
  - Suggested fields: item_id, generated_at, champion_model_name, predicted_mid_price, prediction_interval_low, prediction_interval_high, drift_state, liquidity_status, freshness_status, signal_label.
- GET /api/v1/items/{item_id}/signal
  - Returns an action-oriented signal for one or more horizons.
  - Suggested fields: signal_label, score, reason_codes, guardrail_status, horizon_hours.
  - Allowed signal labels: stable, caution, avoid.
- GET /api/v1/items/{item_id}/explanation
  - Returns the evidence bundle behind the signal.
  - Suggested fields: champion_model_name, mae, directional_accuracy, liquidity_observations_dropped, drift_ratio, interval_width, freshness_minutes.

Phase 4+ decision routes:

- GET /api/v1/recommendations
  - Returns ranked items for a horizon with signal label, score, reason codes, and guardrail status.
  - Scores are derived from SynthesisService rather than hardcoded values.
- GET /api/v1/rankings
  - Supports filter params: signal_label, liquidity_status, drift_state, and top_n.
- GET /api/v1/watchlists
  - Lists saved watchlists.
- POST /api/v1/watchlists
  - Creates a saved watchlist with a name and item ID list.
- GET /api/v1/watchlists/{watchlist_id}
  - Returns a saved watchlist by ID.
- DELETE /api/v1/watchlists/{watchlist_id}
  - Deletes a saved watchlist by ID.

Phase 6 analysis routes (cycle 2):

- GET /api/v1/cohort-comparison
  - Accepts a list of item IDs and returns their current signal state side by side for a requested horizon.

Phase 7 operational routes:

- GET /api/v1/operational-summary
  - Returns generated_at, service_status, freshness_status, warnings, and latest_ingested_at.
  - Freshness is derived from the newest persisted price observation timestamp.

## Response conventions

- JSON response bodies only.
- Timestamps are ISO 8601 UTC.
- Consistent envelope for errors:
  - code
  - message
  - details (optional)
  - request_id (future)

## Pagination

Phase 1 list routes should support cursor or limit/offset with explicit defaults and max limits.

## Validation

- Path IDs must be positive integers.
- Horizon values must be from configured horizon set.
- Date range filters must be UTC and valid.

## Error handling

- 400 for invalid filters.
- 404 for missing entities.
- 422 for schema validation failures.
- 503 for dependency unavailability where applicable.

## Health endpoints

- /health/live: process liveness only.
- /health/ready: dependency checks (database in Phase 0).
