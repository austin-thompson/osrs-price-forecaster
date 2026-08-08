# ADR 0001: Modular monolith over microservices

Status: Accepted

## Context

The project is at an early stage, local-first, and relies on tightly coupled workflows across ingestion, forecasting, and API read models.

## Decision

Adopt a modular monolith with explicit boundaries (API, application, domain, infrastructure, workers) in a single repository and deployable image.

## Consequences

- Faster iteration and lower operational complexity.
- Clear boundaries preserve future extraction paths.
- Team must enforce boundary discipline to avoid tight coupling.

## Alternatives considered

- Early microservices split by function.
  - Rejected due to unnecessary deployment and coordination overhead in MVP phases.
