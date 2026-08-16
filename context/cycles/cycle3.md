# Cycle 3 — Analyst workflow and reliability refinement

Branch: feat/cycle3_analyst-workflow
Started: 2026-08-08
Status: Active (2026-08-16)

## Objective

Turn the existing MVP surfaces into a more repeatable analyst workflow by improving saved analysis, explanation depth, and operational confidence without expanding into a broad application platform.

## Scope

- Complete the Phase 8 personalization slice with saved filters and horizon preferences.
- Improve Phase 6 analysis depth with clearer comparison narratives and supporting evidence.
- Harden Phase 7 operational surfaces with configurable freshness thresholds and more actionable warnings.
- Keep the implementation aligned with the existing local-first forecasting product boundary.

## Non-goals

- A redesigned user interface.
- Multi-user accounts or collaborative workflows.
- Autonomous trading or execution.
- A broad enterprise monitoring platform.

## Proposed phases

### Phase A — Saved analysis preferences

Objective:
Make the analyst workflow reusable by persisting simple analysis preferences instead of forcing repeat configuration.

Deliverables:

- A lightweight preference model for saved filters and horizon defaults.
- CRUD endpoints for saving, listing, retrieving, and deleting preferences.
- Basic validation so bad filter payloads fail clearly and early.

Success criteria:

- A user can save a preferred filter set and horizon choice and reuse it later without re-entering everything.
- The persistence layer follows the same repository patterns used by watchlists.

### Phase B — Richer explanation and comparison views

Objective:
Make the existing analysis surfaces more useful to an analyst by explaining why a signal looks strong or weak.

Deliverables:

- Additional explanation fields that summarize drift, liquidity, model selection, and recency.
- Expanded cohort comparison output with a clearer side-by-side narrative.
- Improved evidence references that point back to the underlying forecast and evaluation signals.

Success criteria:

- Analysts can understand the main driver of a recommendation or comparison without reading the raw model internals.
- The responses remain simple enough to consume from downstream clients.

### Phase C — Operational reliability and freshness handling

Objective:
Make the backend easier to operate by surfacing health and freshness information in a more actionable way.

Deliverables:

- Configurable freshness thresholds for operational summaries.
- More explicit warning conditions for stale ingestion, delayed updates, and weak data quality.
- Clearer separation between service health, data freshness, and signal quality.

Success criteria:

- Operators can identify whether a warning is due to stale data, delayed ingestion, or a degraded signal without needing to inspect the database manually.
- The operational summary remains lightweight and predictable for repeated polling.

## Order of operations

| Step | Work item                                                        | Status    |
| ---- | ---------------------------------------------------------------- | --------- |
| 1    | Define the saved-preference domain and API contract              | Completed |
| 2    | Add the saved-preference migration and repository                | Completed |
| 3    | Implement saved-preference CRUD endpoints and tests              | Pending   |
| 4    | Document analysis endpoint boundaries                            | Pending   |
| 5    | Enrich explanation and cohort-comparison responses               | Pending   |
| 6    | Extract configurable operational freshness thresholds            | Pending   |
| 7    | Add warning classifications and operational regression coverage  | Pending   |
| 8    | Run full live verification and close Cycle 3                     | Pending   |

## Saved-preference contract decision

The Cycle 3 preference is a typed, local-first ranking configuration rather than arbitrary settings
JSON. It stores a name, configured forecast horizon, signal/liquidity/drift filter lists, top-N limit,
and an optional watchlist reference. Empty filter lists mean no restriction. Filter vocabularies and
request/response behavior are normative in API_DESIGN.md; persistence details are normative in
DATA_MODEL.md.

Watchlist deletion sets the preference reference to null rather than deleting the preference. This
keeps the saved filters reusable and avoids coupling the lifecycle of the two analyst artifacts.

## Risks and guardrails

- Scope drift into a full application UI should be avoided.
- Personalization features should remain lightweight and local-first.
- Explanations should help analysts reason about signals without becoming overly verbose or speculative.
- Operational improvements should stay focused on observability and recovery clarity rather than broad platform monitoring.

## Proposed acceptance criteria

- Saved filters and horizon preferences can be created, read, listed, and reused without reconfiguration.
- Comparison and explanation responses give analysts a clearer story about signal behavior, evidence, and recent performance.
- Operational summaries expose clearer freshness and warning states that are actionable for operators.
- New behavior is covered by tests and documented in the relevant context files.
