# Context Documents

This directory is the architectural source of truth for osrs-price-forecaster.

## Why this directory exists

- Keep product intent, architecture, and delivery phases explicit.
- Reduce drift between implementation and design.
- Provide a stable onboarding path for both humans and coding agents.

## Recommended reading order

1. PRODUCT.md
2. ARCHITECTURE.md
3. ROADMAP.md
4. DATA_MODEL.md
5. API_INTEGRATION.md
6. FORECASTING.md
7. Relevant ADRs under adr/
8. TESTING.md, OPERATIONS.md, SECURITY.md

For phase verification history and completion checklists, see the "Phase 1 Completion Evidence (2026-08-02)", "Phase 2 Verification Evidence (2026-08-02)", "Phase 2 Benchmark Checklist", and "Phase 2 Benchmark Run (2026-08-03)" sections in TESTING.md.

## Current MVP-slice status (2026-08-08)

Phases 0–4 and the initial phase 5–8 MVP slices are complete. Cycle 3 analyst-workflow and reliability refinement is also complete and recorded in [cycles/cycle3.md](cycles/cycle3.md).

For the full delivery history and verification evidence, see [cycles/cycle1.md](cycles/cycle1.md) and [TESTING.md](TESTING.md).

## Cycle planning

Per-cycle planning and delivery records live in [cycles/](cycles/). Each cycle file holds gap analysis, order of operations, and status tracking. The ROADMAP holds only stable phase definitions.

## Normative documents

The following are normative and should be treated as binding unless superseded by an accepted ADR:

- PRODUCT.md
- ARCHITECTURE.md
- ROADMAP.md
- DATA_MODEL.md
- API_INTEGRATION.md
- FORECASTING.md
- API_DESIGN.md
- ADRs in adr/

Other documents are guidance but still expected to stay consistent with code.

## Updating architecture decisions

- Record decision changes through a new ADR or an ADR status update.
- Update impacted context docs in the same change.
- Reference decision IDs in PR descriptions and commit messages when possible.

## How humans and coding agents should use this context

- Read this file first.
- Read only the subset relevant to the change, then verify no contradictory statements elsewhere.
- Prefer explicit contradiction resolution over implicit interpretation.

## Conflict policy

If implementation and documentation conflict, resolve explicitly:

1. Decide which source is intended to be correct.
2. Update the stale source immediately.
3. Capture rationale in an ADR when the decision is architectural.
