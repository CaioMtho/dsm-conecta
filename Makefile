FLUTTER ?= $(shell command -v fvm >/dev/null 2>&1 && echo "fvm flutter" || echo "flutter")

.PHONY: install up-all up-infra run-simulator test lint

install:
	uv sync --all-packages
	cd apps/client && $(FLUTTER) pub get

up-all:
	docker compose up -d

up-infra:
	docker compose up -d db broker

run-simulator:
	cd apps/simulator && uv run python -m src.main

test:
	uv run pytest
	cd apps/client && $(FLUTTER) test

lint:
	uv run ruff check .
	cd apps/client && $(FLUTTER) analyze
