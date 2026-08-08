# Data Model

## Tables

### items

Purpose:
Normalized item metadata from mapping endpoint.

Columns (proposed):

- id BIGSERIAL PK
- item_id INTEGER NOT NULL UNIQUE
- name TEXT NOT NULL
- examine TEXT NULL
- tradeable BOOLEAN NOT NULL DEFAULT true
- noted_item_id INTEGER NULL
- high_alch INTEGER NULL
- low_alch INTEGER NULL
- limit INTEGER NULL
- wiki_icon TEXT NULL
- source_updated_at TIMESTAMPTZ NULL
- first_seen_at TIMESTAMPTZ NOT NULL
- last_seen_at TIMESTAMPTZ NOT NULL

Natural key:

- item_id

### ingestion_runs

Purpose:
Track collector runs and partial failures.

Columns:

- id UUID PK
- started_at TIMESTAMPTZ NOT NULL
- completed_at TIMESTAMPTZ NULL
- status TEXT NOT NULL
- endpoint TEXT NOT NULL
- items_requested INTEGER NOT NULL
- observations_received INTEGER NOT NULL
- error_count INTEGER NOT NULL
- metadata JSONB NOT NULL DEFAULT '{}'::jsonb

### price_observations

Purpose:
Store normalized 5m/1h/latest observations with source and ingestion timestamps.

Columns:

- id BIGSERIAL PK
- item_id INTEGER NOT NULL REFERENCES items(item_id)
- interval TEXT NOT NULL
- source_timestamp TIMESTAMPTZ NOT NULL
- ingested_at TIMESTAMPTZ NOT NULL
- avg_high_price INTEGER NULL
- avg_low_price INTEGER NULL
- high_price_volume BIGINT NULL
- low_price_volume BIGINT NULL
- mid_price NUMERIC(14,4) NULL
- ingestion_run_id UUID NULL REFERENCES ingestion_runs(id)
- source_payload_hash TEXT NULL

Uniqueness and idempotency:

- UNIQUE (item_id, interval, source_timestamp)

This tolerates out-of-order arrivals by keying on source semantics.

Indexes:

- idx_price_observations_item_interval_source_ts on (item_id, interval, source_timestamp DESC)
- idx_price_observations_ingested_at on (ingested_at DESC)

### forecast_runs

Purpose:
Track forecaster execution batches.

Columns:

- id UUID PK
- started_at TIMESTAMPTZ NOT NULL
- completed_at TIMESTAMPTZ NULL
- status TEXT NOT NULL
- metadata JSONB NOT NULL DEFAULT '{}'::jsonb

### forecasts

Purpose:
Persist historical predictions immutably.

Columns:

- id BIGSERIAL PK
- item_id INTEGER NOT NULL REFERENCES items(item_id)
- horizon_hours INTEGER NOT NULL
- interval TEXT NOT NULL
- forecast_created_at TIMESTAMPTZ NOT NULL
- forecast_target_at TIMESTAMPTZ NOT NULL
- predicted_mid_price NUMERIC(14,4) NOT NULL
- model_name TEXT NOT NULL
- model_version TEXT NOT NULL
- training_window_start TIMESTAMPTZ NULL
- training_window_end TIMESTAMPTZ NULL
- forecast_run_id UUID NULL REFERENCES forecast_runs(id)
- metadata JSONB NOT NULL DEFAULT '{}'::jsonb

Uniqueness:

- UNIQUE (item_id, horizon_hours, forecast_created_at, forecast_target_at, model_name, model_version)

### model_evaluations

Purpose:
Store candidate model scores by item and horizon.

Columns:

- id BIGSERIAL PK
- item_id INTEGER NOT NULL REFERENCES items(item_id)
- horizon_hours INTEGER NOT NULL
- model_name TEXT NOT NULL
- model_version TEXT NOT NULL
- evaluation_window_start TIMESTAMPTZ NOT NULL
- evaluation_window_end TIMESTAMPTZ NOT NULL
- metric_mae NUMERIC(14,4) NULL
- metric_rmse NUMERIC(14,4) NULL
- metric_smape NUMERIC(8,4) NULL
- metric_directional_accuracy NUMERIC(8,4) NULL
- metric_bias NUMERIC(14,4) NULL
- created_at TIMESTAMPTZ NOT NULL
- metadata JSONB NOT NULL DEFAULT '{}'::jsonb

### model_selections

Purpose:
Track selected champion and reason by item+horizon.

Columns:

- id BIGSERIAL PK
- item_id INTEGER NOT NULL REFERENCES items(item_id)
- horizon_hours INTEGER NOT NULL
- selected_model_name TEXT NOT NULL
- selected_model_version TEXT NOT NULL
- primary_metric TEXT NOT NULL
- primary_metric_value NUMERIC(14,4) NULL
- reason TEXT NOT NULL
- selected_at TIMESTAMPTZ NOT NULL
- evaluation_id BIGINT NULL REFERENCES model_evaluations(id)

Uniqueness:

- UNIQUE (item_id, horizon_hours, selected_at)

## Timestamp semantics

- source_timestamp: timestamp from OSRS source data.
- ingested_at: when this system persisted the observation.
- forecast_created_at: when prediction was generated.
- forecast_target_at: timestamp being predicted.
- evaluation timestamp fields are explicit and separate.

## Retention considerations

- Keep raw normalized observations for reproducible backtesting.
- Historical forecasts and evaluations should be append-only.
- Introduce retention/archiving policy only after observed storage pressure.

## Partitioning guidance

PostgreSQL partitioning may become appropriate for price_observations and forecasts when row counts and write rates materially impact maintenance and query performance. Not implemented in Phase 0.
