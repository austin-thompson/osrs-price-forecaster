# Operations

## Local startup

1. Copy .env.example to .env and adjust as needed.
2. Run docker compose up --build for postgres + api.
3. Run alembic upgrade head inside the environment before full workflows.

## Migration workflow

- New migration: make revision m="describe change"
- Apply migration: make migrate
- Do not use metadata.create_all() at app startup.

## Collector execution

- Collector is a separate process from the same image.
- Enabled through compose profile workers.
- Live collection requires descriptive User-Agent configuration.

## Logging

- Structured JSON logs.
- Include event, component, duration, IDs, and counts.
- Avoid full payload dumps by default.

## Health checks

- /health/live for process liveness.
- /health/ready for dependency readiness.
- /api/v1/operational-summary for ingestion freshness and service health status.

## Graceful shutdown

- API and workers rely on process signals and context-managed resources.
- Ensure HTTP clients and DB engines are closed on shutdown.

## Backup considerations

- Local postgres volume can be snapshotted with pg_dump.
- Forecast and evaluation history should be retained for reproducibility.

## Failure recovery

- ingestion_runs and forecast_runs capture partial failures.
- Jobs should be idempotent where possible.

## Data replay

- Historical backfill through timeseries endpoint is Phase 1.
- Keep schema suitable for replay-based recovery.

## Configuration

All runtime options are environment-driven through pydantic-settings.

Operational ingestion freshness uses two positive minute thresholds:

- `OPERATIONAL_FRESHNESS_WARNING_MINUTES` defaults to 90.
- `OPERATIONAL_FRESHNESS_STALE_MINUTES` defaults to 180 and must be greater than the warning
  threshold.

The operational summary is healthy below the warning threshold, warning at or above the warning
threshold, and stale at or above the stale threshold. Invalid threshold ordering prevents startup
instead of silently producing ambiguous freshness states.

## Future observability

Metrics and tracing are planned for later phases when needed.

## CI/CD posture

CI/CD is intentionally deferred while the project is local-first and single-developer. Manual Git tags with GitHub Releases serve as lightweight release markers in the interim.

## Release workflow

Tag and publish a release only after a squash-merge into main:

```bash
git tag v0.x.0-alpha
git push origin v0.x.0-alpha
gh release create v0.x.0-alpha --title "v0.x.0-alpha" --notes "Brief description of what this cycle delivered."
```

Rules:

- Never tag a feature branch or an intermediate commit on main.
- Always create a GitHub Release from the tag immediately after pushing it — a raw tag with no release is incomplete.
- Release notes should summarise what the cycle delivered at a cycle level, not commit by commit.

A GitHub Actions workflow should be introduced when:

- The unit and integration test suite is stable enough to gate pull requests automatically.
- The Docker build is confirmed reproducible across environments.
- There is a clear deployment target (even a simple one) that benefits from automated delivery.

When that point is reached, the workflow should cover at minimum: dependency install, lint, typecheck, and the full test suite. A Docker build check and migration dry-run would be the next logical additions. A dedicated CI/CD context document can be created at that point to record workflow design decisions.
