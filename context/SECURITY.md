# Security

## Scope

Phase 0 security focuses on sane local defaults and avoiding avoidable risk.

## Secrets management

- Use environment variables.
- Do not commit secrets.
- Keep .env out of version control.

## Dependency scanning

- CI should run dependency and code scanning over time.
- Keep dependencies minimal and pinned by lockfile.

## Input validation

- Validate all external payloads via DTO schemas.
- Validate API request parameters via FastAPI/Pydantic.

## SQL injection prevention

- Use SQLAlchemy query construction and bound parameters.
- Avoid raw SQL string interpolation.

## Log redaction

- Avoid logging credentials and full third-party payloads.
- Keep debug logging off by default.

## HTTP client safety

- Explicit timeout values.
- Retry only transient failures.
- Respect external API limits.

## Supply chain considerations

- Prefer well-maintained libraries.
- Keep CI checks and review dependency changes deliberately.

## API abuse prevention

Local MVP is not public, but future phases should add request throttling and authentication before internet exposure.

## Future auth boundaries

Authentication and authorization are deferred to Phase 4 and must be introduced at API/application boundaries without polluting domain logic.
