#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf "\n==> %s\n" "$1"
}

log "Stopping local services"
docker compose stop api postgres >/dev/null 2>&1 || true

printf "Local environment stopped.\n"
