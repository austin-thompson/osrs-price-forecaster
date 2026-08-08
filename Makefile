SHELL := /bin/bash
PYTHON ?= python
UV := $(PYTHON) -m uv

.PHONY: help install format lint typecheck test test-integration run-api run-collector run-forecaster migrate revision docker-up docker-down

help:
	@echo "Available targets: install, format, lint, typecheck, test, test-integration, run-api, run-collector, run-forecaster, migrate, revision, docker-up, docker-down"

install:
	$(UV) sync --all-groups

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff format --check .
	$(UV) run ruff check .

typecheck:
	$(UV) run mypy src tests

test:
	$(UV) run pytest -m "not integration"

test-integration:
	$(UV) run pytest -m "integration"

run-api:
	$(UV) run uvicorn osrs_price_forecaster.main:app --factory --host 0.0.0.0 --port 8000

run-collector:
	$(UV) run python -m osrs_price_forecaster.workers.collector

run-forecaster:
	$(UV) run python -m osrs_price_forecaster.workers.forecaster

migrate:
	$(UV) run alembic upgrade head

revision:
	$(UV) run alembic revision --autogenerate -m "$(m)"

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
