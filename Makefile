.PHONY: install migrate seed run test lint format demo reset docker-up docker-down

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "Now copy .env.example to .env: cp .env.example .env"

migrate:
	$(VENV)/bin/alembic upgrade head

seed:
	$(PYTHON) -m app.cli seed-demo-data

run:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(VENV)/bin/pytest -q

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .

format:
	$(VENV)/bin/ruff check . --fix
	$(VENV)/bin/black .

# One-shot: migrate + seed + run, for a fresh clone.
demo: migrate seed run

reset:
	$(PYTHON) -m app.cli reset-demo-data

docker-up:
	docker compose up --build

docker-down:
	docker compose down
