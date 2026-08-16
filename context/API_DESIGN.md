# API Design

## Versioning

- Base path: /api/v1
- Additive changes preferred.
- Breaking changes require new major API version.

## Current API surface

This snapshot reflects the implemented routes through Cycle 2 and the planned Cycle 3 extensions.

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

Phase 6 analysis routes (Cycle 2):

- GET /api/v1/items/{item_id}/analysis-summary
  - Returns an analyst-oriented summary of an item’s current signal, supporting evidence, and recent context.
- GET /api/v1/cohort-comparison
  - Accepts a list of item IDs and returns their current signal state side by side for a requested horizon.

Phase 7 operational routes:

- GET /api/v1/operational-summary
  - Returns generated_at, service_status, freshness_status, warnings, and latest_ingested_at.
  - Freshness is derived from the newest persisted price observation timestamp.

Cycle 3 saved-analysis routes:

- GET /api/v1/preferences
  - Lists saved analysis preferences newest first.
- POST /api/v1/preferences
  - Creates a reusable ranking configuration.
- GET /api/v1/preferences/{preference_id}
  - Returns one saved analysis preference by ID.
- DELETE /api/v1/preferences/{preference_id}
  - Deletes one saved analysis preference and returns HTTP 204.

Saved-analysis preference request fields:

- `name`: required, trimmed string with 1–128 characters.
- `horizon_hours`: required and restricted to the configured forecast horizon set.
- `signal_labels`: zero or more unique values from `stable`, `caution`, and `avoid`.
- `liquidity_statuses`: zero or more unique values from `healthy`, `risky`, and `unknown`.
- `drift_states`: zero or more unique values from `improved`, `stable`, `worsened`,
  `insufficient_history`, and `unknown`.
- `top_n`: required integer from 1–500, matching the ranking endpoint limit.
- `watchlist_id`: optional positive integer referencing a saved watchlist.

Empty filter lists mean no restriction for that filter. Duplicate filter values are rejected rather
than silently normalized. A missing referenced watchlist returns HTTP 404. Preference names do not
need to be unique because this remains a local, single-user workflow.

Saved-analysis preference responses add `id` and `created_at` to the request fields. Deleting a
watchlist sets any associated preference `watchlist_id` to null so the remaining filters stay usable.

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
- Saved-preference filter values must use the documented stable vocabularies.

## Error handling

- 400 for invalid filters.
- 404 for missing entities.
- 422 for schema validation failures.
- 503 for dependency unavailability where applicable.

## Health endpoints

- /health/live: process liveness only.
- /health/ready: dependency checks (database in Phase 0).
