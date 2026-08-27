.PHONY: install up-all up-infra run-simulator test lint

install:
	uv sync
	cd apps/client && fvm flutter pub get

up-all:
	docker compose up -d

up-infra:
	docker compose up -d db broker

run-simulator:
	cd apps/simulator && uv run python -m src.main

test:
	uv run pytest
	cd apps/client && fvm flutter test

lint:
	uv run ruff check .
	cd apps/client && fvm flutter analyze
