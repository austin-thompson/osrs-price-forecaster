# Local live run

This workflow starts the local API and database so the project can be exercised end to end without GitHub automation.

## Prerequisites

- Docker is installed and running.
- Python 3.12+ is available.
- The workspace virtual environment exists.

## Start the local environment

From the repository root, run:

```bash
bash scripts/start_local_env.sh
```

The script will:

1. Create a local `.env` file if one does not already exist.
2. Start the local PostgreSQL container.
3. Start the API container.
4. Apply the Alembic migrations via the API container once it is ready.

## Populate data

The database starts empty. Run the collector to sync item mappings and price
observations from the OSRS Wiki:

```bash
docker compose --profile workers run --rm collector
```

The collector fetches:

- Full item mapping (all tradeable items → `items` table)
- Latest 5m and 1h prices for tracked items
- Historical timeseries for tracked items

Tracked items are controlled by `TRACKED_ITEM_IDS` in `.env` (defaults to
`[4151, 11840]`). Add any item IDs you want before running the collector.

Verify data landed:

```bash
docker compose exec -T postgres psql -U postgres -d osrs_price_forecaster -c \
  "SELECT item_id, COUNT(*) AS observations FROM price_observations GROUP BY item_id ORDER BY item_id;"
```

## Verify the live environment

Once the script completes, validate the API with:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

The API docs are available at:

```text
http://localhost:8000/docs
```

## Stop the local environment

Run:

```bash
bash scripts/stop_local_env.sh
```

This stops the API and PostgreSQL containers without removing the local volume data.
