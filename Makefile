FLUTTER ?= $(shell command -v fvm >/dev/null 2>&1 && echo "fvm flutter" || echo "flutter")

.PHONY: install up-all up-dev up-infra run-simulator run-client-dev run-client-remote test test-broker-auth lint

install:
	uv sync --all-packages
	cd apps/client && $(FLUTTER) pub get

up-all:
	docker compose -f deployments/docker-compose.yml up -d

up-dev:
	docker compose -f deployments/docker-compose.yml -f deployments/docker-compose.dev.yml up -d

up-infra:
	docker compose -f deployments/docker-compose.yml up -d --no-build db broker nginx

run-client-dev:
	cd apps/client && $(FLUTTER) run --dart-define-from-file=config/dev.json

run-client-remote:
	cd apps/client && $(FLUTTER) run --dart-define-from-file=config/remote.json

run-simulator:
	cd apps/simulator && uv run python -m src.main

test:
	uv run pytest
	cd apps/client && $(FLUTTER) test

test-broker-auth:
	uv run pytest tests/test_broker_auth.py

lint:
	uv run ruff check .
	cd apps/client && $(FLUTTER) analyze

