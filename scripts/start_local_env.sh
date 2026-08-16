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
postgres_ready=false
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d osrs_price_forecaster >/dev/null 2>&1; then
    postgres_ready=true
    break
  fi
  sleep 2
done
if [[ "$postgres_ready" != true ]]; then
  printf "PostgreSQL did not become healthy within 60 seconds.\n" >&2
  exit 1
fi

log "Starting API"
docker compose up -d api

log "Waiting for API readiness endpoint"
api_ready=false
for _ in $(seq 1 30); do
  if docker compose exec -T api uv run python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=5)" \
    >/dev/null 2>&1; then
    api_ready=true
    break
  fi
  sleep 2
done
if [[ "$api_ready" != true ]]; then
  printf "API readiness endpoint did not become healthy within 60 seconds.\n" >&2
  docker compose logs --tail=50 api >&2
  exit 1
fi

log "Applying database migrations"
docker compose exec -T api uv run alembic upgrade head

log "Local environment is up"
printf "Health: http://localhost:8000/health/live\n"
printf "Ready:  http://localhost:8000/health/ready\n"
printf "Docs:   http://localhost:8000/docs\n"
