#!/usr/bin/env bash
set -euo pipefail

ITEM_ID="${ITEM_ID:-4151}"
HORIZON_HOURS="${HORIZON_HOURS:-1}"
OSRS_WIKI_USER_AGENT="${OSRS_WIKI_USER_AGENT:-}"

log() {
  printf "\n==> %s\n" "$1"
}

diagnose_failure() {
  printf "\nLive verification failed. Current service state:\n" >&2
  docker compose ps >&2 || true
  docker compose logs --tail=50 api >&2 || true
}

assert_positive_count() {
  local description="$1"
  local query="$2"
  local count

  count="$(
    docker compose exec -T postgres \
      psql -v ON_ERROR_STOP=1 -U postgres -d osrs_price_forecaster -tA -c "$query" \
      | tr -d '[:space:]'
  )"
  if [[ ! "$count" =~ ^[0-9]+$ ]] || (( count < 1 )); then
    printf "Expected %s, received count '%s'.\n" "$description" "$count" >&2
    return 1
  fi
  printf "%s: %s\n" "$description" "$count"
}

trap diagnose_failure ERR

if [[ ! "$ITEM_ID" =~ ^[1-9][0-9]*$ ]] || [[ ! "$HORIZON_HOURS" =~ ^[1-9][0-9]*$ ]]; then
  printf "ITEM_ID and HORIZON_HOURS must be positive integers.\n" >&2
  exit 1
fi

if [[ -z "$OSRS_WIKI_USER_AGENT" ]] || [[ "$OSRS_WIKI_USER_AGENT" == *"replace-me@example.com"* ]]; then
  printf "Set OSRS_WIKI_USER_AGENT to a descriptive value with a real contact before running live verification.\n" >&2
  exit 1
fi

log "Starting stack and waiting for health"
docker compose up --build -d --wait

log "Applying latest migrations"
docker compose exec -T api uv run alembic upgrade head

log "Running one collector cycle"
docker compose --profile workers run --rm \
  -e OSRS_WIKI_USER_AGENT="$OSRS_WIKI_USER_AGENT" collector

log "Running one forecaster cycle"
docker compose --profile future run --rm \
  -e OSRS_WIKI_USER_AGENT="$OSRS_WIKI_USER_AGENT" forecaster

log "Checking health endpoints"
curl --fail --show-error --silent "http://localhost:8000/health/live" && printf "\n"
curl --fail --show-error --silent "http://localhost:8000/health/ready" && printf "\n"

log "Checking live verification API endpoints for item ${ITEM_ID}, horizon ${HORIZON_HOURS}"
curl --fail --show-error --silent \
  "http://localhost:8000/api/v1/items/${ITEM_ID}/backtesting-report?horizon_hours=${HORIZON_HOURS}" && printf "\n"
curl --fail --show-error --silent \
  "http://localhost:8000/api/v1/items/${ITEM_ID}/forecasts?horizon_hours=${HORIZON_HOURS}&limit=3" && printf "\n"
curl --fail --show-error --silent \
  "http://localhost:8000/api/v1/items/${ITEM_ID}/model-performance?horizon_hours=${HORIZON_HOURS}&limit=5" && printf "\n"

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

assert_positive_count \
  "model evaluation rows" \
  "SELECT COUNT(*) FROM model_evaluations;"
assert_positive_count \
  "forecast rows for item ${ITEM_ID} and horizon ${HORIZON_HOURS}" \
  "SELECT COUNT(*) FROM forecasts WHERE item_id = ${ITEM_ID} AND horizon_hours = ${HORIZON_HOURS};"
assert_positive_count \
  "forecasts with drift and interval metadata" \
  "SELECT COUNT(*) FROM forecasts WHERE metadata ? 'drift_state' AND metadata ? 'prediction_interval_low' AND metadata ? 'prediction_interval_high';"

trap - ERR
log "Live verification complete"
