# Product Definition

## Problem statement

Old School RuneScape market participants need transparent, local-first tooling to inspect recent Grand Exchange price behavior, generate forecasts, and evaluate whether forecast quality is improving over time.

## Target user

- Individual players, makers, and analysts who want reproducible local analysis.
- Developers who want a clean forecasting architecture without cloud lock-in.

## Core use cases

- Track selected item prices over time with data provenance.
- Generate forecasts for configured horizons.
- Compare forecast quality by model and horizon.
- Audit historical predictions against realized outcomes.

## Product principles

- A forecast without an evaluation history is merely a decorated opinion.
- Historical integrity is mandatory: never rewrite past predictions.
- Keep architecture simple until complexity is justified by measured bottlenecks.
- Prefer explicit contracts over hidden conventions.

## MVP boundaries

The current MVP focus remains:

- Item mapping + 5-minute and 1-hour observation ingestion.
- Baseline forecasting candidates.
- Walk-forward evaluation and per-item/per-horizon champion selection.
- API endpoints for items, prices, forecasts, and model performance.
- Readable synthesis and recommendation outputs that explain the current signal.

## Current MVP-slice status (Phases 5-8)

The current implementation has completed the initial MVP slices for the later analyst-facing phases:

- Phase 5: ranking and recommendation outputs now expose synthesis-backed scores, signal labels, reason codes, and champion-model metadata for requested horizons.
- Phase 6: analysis-summary and cohort-comparison endpoints now provide compact signal views and side-by-side multi-item comparisons.
- Phase 7: the operational-summary endpoint now exposes service health, freshness status, warnings, and the latest ingested observation timestamp from persisted price data.
- Phase 8: watchlists can now be created, listed, fetched, and deleted through a simple persisted endpoint set.

What remains beyond these first slices:

- Phase 5 still benefits from richer portfolio-style ranking behavior and more sophisticated watchlist workflows.
- Phase 6 still needs deeper comparison, benchmark-history, and explanation workflows beyond the current single-item and cohort views.
- Phase 7 now provides meaningful health and freshness reporting, and can continue to expand as operational monitoring needs mature.
- Phase 8 still needs richer personalization features such as saved filters, horizon preferences, and local annotations, plus fetch/delete support for watchlists.

The next expansion phases are intended to improve usability and comparability for analysts, not to broaden the product into unrelated experiences. The current Phase 5-8 slices keep the scope tight while proving the API contract for ranking, analysis summaries, operational visibility, and simple saved watchlists without drifting into UI polish or speculative features. While the MVP is still being completed, future phase design should stay tightly scoped to transparent forecasting, ranking, explainability, reliability, and lightweight personalization work.

## Non-goals

- Automated trading.
- Guaranteed-profit recommendations.
- Public multi-tenant hosting in MVP.
- RuneLite account integration.

## Risks and limitations

- External API schema changes may break ingestion.
- Low-liquidity items can produce unstable forecasts.
- Data latency and staleness can impact apparent model quality.

## Attribution and disclaimers

- This project is not affiliated with Jagex, RuneLite, or the OSRS Wiki.
- Forecasts are experimental and are not guaranteed profit signals.
