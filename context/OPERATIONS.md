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

## Future observability

Metrics and tracing are planned for later phases when needed.
