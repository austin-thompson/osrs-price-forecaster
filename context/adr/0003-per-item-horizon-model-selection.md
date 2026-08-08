# ADR 0003: Per-item and per-horizon model selection

Status: Accepted

## Context

OSRS items exhibit heterogeneous behavior by liquidity, volatility, and regime. Forecast utility varies by horizon.

## Decision

Model selection will be performed independently per (item_id, forecast_horizon), with stored evaluation metrics and explicit selection reasons.

## Consequences

- Better fit to item-specific and horizon-specific dynamics.
- More evaluation and storage complexity than a single global model.
- Requires disciplined reproducibility and model version tracking.

## Alternatives considered

- One global model for all items and horizons.
  - Rejected due to likely underfitting and opaque trade-offs.
- One model per item only.
  - Rejected because horizon behavior differs materially.
