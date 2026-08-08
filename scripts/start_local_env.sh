#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf "\n==> %s\n" "$1"
}

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

log "Starting PostgreSQL"
docker compose up -d postgres

log "Waiting for PostgreSQL to become healthy"
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d osrs_price_forecaster >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

log "Starting API"
docker compose up -d api

log "Waiting for API to become healthy"
for _ in $(seq 1 30); do
  if docker compose exec -T api uv run python -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

log "Applying database migrations"
docker compose exec -T api uv run alembic upgrade head

log "Local environment is up"
printf "Health: http://localhost:8000/health/live\n"
printf "Ready:  http://localhost:8000/health/ready\n"
printf "Docs:   http://localhost:8000/docs\n"
