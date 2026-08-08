# Forecasting Design

## Target variable

Canonical target for initial models:
mid_price = (avg_high_price + avg_low_price) / 2

Only computed when both prices are present and valid.

## Forecast horizons

Represented generically in domain contracts.
Planned defaults: 1h, 6h, 24h.

## Candidate model protocol

Contracts include:

- feature generation
- model training
- forecast generation
- model evaluation
- model selection
- prediction persistence
- candidate registration

## Training window semantics

Training windows are explicit and stored with outputs where applicable.

## Minimum-data requirements

Selection must require a configurable minimum observation count before non-naive candidates are eligible.

## Validation strategy

Use rolling-origin / walk-forward validation only.
Do not use random train/test splits for time-series.

## Evaluation metrics

Planned metrics:

- MAE (primary MVP metric)
- RMSE
- sMAPE
- Directional accuracy
- Interval coverage (future)
- Forecast bias

## Champion/challenger model selection

Champion is selected per (item_id, forecast_horizon) using the configured metric priority and minimum-data rules. Challenger scores remain persisted for auditability.

## Fallback behavior

Fallback to naive model where insufficient data exists.

## Prediction intervals

Implemented in Phase 2 for baseline workflows using residual quantiles from walk-forward errors.
Forecast metadata persists confidence level and interval bounds.

## Reproducibility

- Persist model name/version with each forecast.
- Store evaluation windows and metrics.
- Keep historical predictions immutable.

## Data leakage prevention

- No future observations in training relative to forecast creation.
- Keep timestamp roles explicit and separate.

## Timestamp distinctions

- Data timestamp: when market value applies (source_timestamp).
- Forecast creation timestamp: when model generated prediction.
- Forecast target timestamp: time being predicted.
- Evaluation timestamp: when realized outcome comparison was computed.

## Low-liquidity considerations

Low or zero volume intervals may produce unstable signals and should be identified for diagnostics and future filtering.
Phase 2 introduces minimum-volume liquidity filtering before model evaluation/training.

## Drift detection

Phase 2 computes simple drift signals by comparing latest MAE vs previous MAE per model/item/horizon:

- worsened: ratio >= 1.25
- stable: 0.85 < ratio < 1.25
- improved: ratio <= 0.85

Signals are surfaced in selection rationale and forecast metadata.

## Phase 2 benchmark definitions

The following benchmark definitions are used for Phase 2 completion evaluation:

- Baseline comparator:
  - Phase 1 baseline run metrics (naive + rolling mean) captured in `model_evaluations` before enabling Phase 2 candidate expansion.
- Evaluation population:
  - Tracked items only.
  - Horizons: 1h, 6h, 24h.
  - Minimum folds per (item, horizon, model): 50.
- Improvement rule:
  - Primary metric: MAE.
  - Completion threshold: at least 2 improving item/horizon cells vs Phase 1 baseline, with worst-cell regression no worse than -2%.
- Interval calibration rule:
  - Confidence target: 80%.
  - Forecast metadata must persist interval bounds and confidence.
  - Empirical coverage query is maintained and executed on realized benchmark windows.
- Drift reporting rule:
  - Forecast metadata and selection reason must include drift signal fields for evaluated horizons.

## Synthesis layer

The backend should expose synthesized views that collapse raw forecast rows into a compact decision artifact. A useful shape for each item/horizon is:

- current champion model
- confidence band width
- drift state
- liquidity health
- recency freshness
- recommendation label and supporting reason codes

For Phase 3, this should be derived from persisted evaluation and forecast metadata rather than recomputed ad hoc in the API layer. The first implementation should use existing tables and avoid introducing a new storage schema until the synthesis contract is stable.

## Phase 3 synthesis heuristics

The first practical synthesis rules should be simple and explicit:

- freshness_status: derived from the age of the latest forecast relative to the current time.
- liquidity_status: derived from the latest liquidity filter outcome and the number of observations dropped.
- confidence_band: derived from the interval width relative to the point forecast.
- signal_label: derived from a small rule set:
  - stable: forecast exists, liquidity is acceptable, and drift is neutral.
  - caution: drift is elevated, interval width is wide, or freshness is moderate.
  - avoid: liquidity is below threshold, data is stale, or confidence is too weak to support action.

Each signal should carry the evidence that produced it, such as champion model, interval width, liquidity drop count, recent drift ratio, and recency.

## Decision signals

Once synthesis exists, the platform can derive simple action-oriented signals with explicit guardrails:

- stable: signal is present and confidence/liquidity are acceptable
- caution: drift or volatility is elevated but evidence is not yet decisive
- avoid: liquidity, freshness, or model confidence fail minimum thresholds

Every signal should carry the evidence that produced it, such as champion model, interval width, liquidity drop count, and recent drift ratio.

## Future feature candidates

- spread features
- volatility windows
- day-of-week seasonality
- event annotations
- cross-item relationships
- portfolio-level ranking heuristics
