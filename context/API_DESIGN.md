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
  - Returns the canonical current-state snapshot for one item and horizon.
  - Includes forecast values and uncertainty, champion-model identity, drift, liquidity,
    freshness, and the derived signal.
- GET /api/v1/items/{item_id}/signal
  - Returns the smallest action-oriented decision contract for one item and horizon.
  - Includes signal_label, score, reason_codes, guardrail_status, and horizon_hours.
  - Allowed signal labels: stable, caution, avoid.
- GET /api/v1/items/{item_id}/explanation
  - Returns supporting model, liquidity, drift, uncertainty, and recency diagnostics.
  - Includes champion_model_name, mae, directional_accuracy,
    liquidity_observations_dropped, drift_ratio, interval_width, freshness_minutes,
    and evidence-specific reason codes.

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
  - Returns a convenience composition of the signal, selected current-state fields, and
    explanation metrics for a single-item analyst overview.
- GET /api/v1/cohort-comparison
  - Accepts a list of item IDs and returns compact current signal state side by side for
    one requested horizon, retaining request order.

### Analysis endpoint boundaries

The analysis routes intentionally overlap so clients can choose the smallest response that fits a
workflow. Their responsibilities remain distinct:

| Endpoint | Authoritative responsibility | Intended client use | Out of scope |
| --- | --- | --- | --- |
| `/items/{item_id}/summary` | Complete current forecast state for one item and horizon, including prediction values, interval bounds, model, market-state classifications, and signal | Render or inspect the latest item state | Detailed evaluation diagnostics or historical backtest data |
| `/items/{item_id}/signal` | Recommendation label, score, guardrail, and the reasons used for that decision | Gate, filter, or label an item with the smallest decision payload | Forecast values and model-performance diagnostics |
| `/items/{item_id}/explanation` | Evidence supporting interpretation of the current result, including model quality, drift, liquidity loss, uncertainty, and freshness | Explain why evidence is strong, weak, or incomplete | An independent recommendation; its evidence reason codes do not replace the signal's decision reasons |
| `/items/{item_id}/analysis-summary` | Convenience composition of signal fields, selected summary state, and explanation metrics | Populate a single-item analyst overview without coordinating three requests | Full forecast detail, interval bounds, or complete backtest history |
| `/cohort-comparison` | Compact, same-horizon side-by-side state for requested items | Compare a caller-selected cohort while preserving caller order | Sorting or discovering the best items; use `/rankings` for ranked output |

Shared rules:

- Each request uses one configured forecast horizon; comparisons do not mix horizons.
- The `/signal` response is authoritative for recommendation label, score, guardrail, and decision
  reason codes wherever those fields also appear in a composite response.
- The `/summary` response is authoritative for current forecast values and market-state
  classifications; `/explanation` is authoritative for its diagnostic metrics.
- Composite routes preserve those source semantics and must not redefine duplicated fields.
- Missing or incomplete analytical evidence is represented by stable fallback states and reason
  codes where the underlying synthesis service supports them; no route implies guaranteed profit.

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
