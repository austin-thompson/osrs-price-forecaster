# Scripts

Utility scripts can be added here as operational workflows grow.

## Local live environment

Use the helper scripts for the local API/database workflow:

- `bash scripts/start_local_env.sh` — starts PostgreSQL, applies migrations, and starts the API
- `bash scripts/stop_local_env.sh` — stops both containers without removing data

After starting, run the collector once to populate items and price observations:

```bash
docker compose --profile workers run --rm collector
```

See [scripts/LOCAL_LIVE_RUN.md](LOCAL_LIVE_RUN.md) for the full workflow and expected URLs.

## Live verification

Run the end-to-end live check workflow:

- `bash scripts/live_verification.sh`

Optional environment overrides:

- `OSRS_WIKI_USER_AGENT` (default: `osrs-price-forecaster/0.2.0-alpha (contact: local-dev@example.com)`)
- `ITEM_ID` (default: `4151`)
- `HORIZON_HOURS` (default: `1`)
