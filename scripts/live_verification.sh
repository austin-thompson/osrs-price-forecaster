#!/usr/bin/env bash
set -euo pipefail

ITEM_ID="${ITEM_ID:-4151}"
HORIZON_HOURS="${HORIZON_HOURS:-1}"

log() {
  printf "\n==> %s\n" "$1"
}

log "Starting stack and waiting for health"
docker compose up --build -d --wait

log "Applying latest migrations"
docker compose exec -T api uv run alembic upgrade head

log "Running one collector cycle"
docker compose --profile workers run --rm collector

log "Running one forecaster cycle"
docker compose --profile future run --rm forecaster

log "Checking health endpoints"
curl -sS "http://localhost:8000/health/live" && printf "\n"
curl -sS "http://localhost:8000/health/ready" && printf "\n"

log "Checking live verification API endpoints for item ${ITEM_ID}, horizon ${HORIZON_HOURS}"
curl -sS "http://localhost:8000/api/v1/items/${ITEM_ID}/backtesting-report?horizon_hours=${HORIZON_HOURS}" && printf "\n"
curl -sS "http://localhost:8000/api/v1/items/${ITEM_ID}/forecasts?horizon_hours=${HORIZON_HOURS}&limit=3" && printf "\n"
curl -sS "http://localhost:8000/api/v1/items/${ITEM_ID}/model-performance?horizon_hours=${HORIZON_HOURS}&limit=5" && printf "\n"

log "Checking model coverage and metadata persistence in PostgreSQL"
docker compose exec -T postgres psql -U postgres -d osrs_price_forecaster -c "
SELECT model_name, model_version, COUNT(*) AS eval_count
FROM model_evaluations
GROUP BY model_name, model_version
ORDER BY model_name;
"

docker compose exec -T postgres psql -U postgres -d osrs_price_forecaster -c "
SELECT item_id, horizon_hours, COUNT(*) AS forecast_count
FROM forecasts
GROUP BY item_id, horizon_hours
ORDER BY item_id, horizon_hours;
"

docker compose exec -T postgres psql -U postgres -d osrs_price_forecaster -c "
SELECT
  COUNT(*) FILTER (WHERE metadata ? 'drift_state') AS with_drift,
  COUNT(*) FILTER (WHERE metadata ? 'prediction_interval_low' AND metadata ? 'prediction_interval_high') AS with_interval_bounds,
  COUNT(*) AS total
FROM forecasts;
"

log "Live verification complete"
