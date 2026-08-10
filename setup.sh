#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[setup] %s\n' "$1"
}

wait_for_postgres() {
  local attempts=0
  local max_attempts=24
  while [ "$attempts" -lt "$max_attempts" ]; do
    local status
    status="$(docker inspect --format='{{json .State.Health.Status}}' smart-retail-postgres 2>/dev/null || true)"
    if [ "$status" = '"healthy"' ]; then
      return 0
    fi
    attempts=$((attempts + 1))
    printf '[setup] Waiting for PostgreSQL healthcheck (%s/%s)\n' "$attempts" "$max_attempts"
    sleep 5
  done

  printf '[setup] PostgreSQL did not become healthy in time\n' >&2
  return 1
}

if [ ! -f .env ]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [ ! -d .venv ]; then
  log "Creating local virtual environment"
  "$PYTHON_BIN" -m venv .venv
fi

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  # shellcheck disable=SC1091
  . .venv/Scripts/activate
fi

log "Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Starting PostgreSQL container"
docker compose up -d postgres
wait_for_postgres

log "Running ETL pipeline container"
docker compose run --rm pipeline

log "Pipeline execution finished"
printf '\nPower BI connection:\n'
printf 'Host: localhost\nPort: 5432\nDatabase: %s\nUser: %s\nSchema: %s\n' \
  "${DATABASE_NAME:-smart_retail}" "${DATABASE_USER:-postgres}" "${DATABASE_SCHEMA:-analytics}"