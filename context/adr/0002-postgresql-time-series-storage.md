# ADR 0002: PostgreSQL before specialized time-series infrastructure

Status: Accepted

## Context

The initial workload is local and moderate. Team needs transactional consistency, simplicity, and strong relational support for forecasts, evaluations, and selections.

## Decision

Use PostgreSQL as the only primary store in Phase 0 and Phase 1. Defer specialized time-series storage and partitioning until measured bottlenecks justify it.

## Consequences

- Simpler deployment and backups.
- Strong transactional and indexing capabilities.
- Potential future migration effort if scale outgrows baseline design.

## Alternatives considered

- TimescaleDB in MVP.
  - Rejected as premature optimization.
- Multi-store architecture (OLTP + TSDB).
  - Rejected for added complexity before need is proven.
