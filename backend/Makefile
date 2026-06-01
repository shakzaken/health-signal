.PHONY: run dev install migrate migration downgrade db-reset lint format test help

# ── Dev server ───────────────────────────────────────────────────────────────

run:
	uv run uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ── Dependencies ─────────────────────────────────────────────────────────────

install:
	uv sync

# ── Database ─────────────────────────────────────────────────────────────────

migrate:
	uv run alembic upgrade head

# Usage: make migration msg="add user table"
migration:
	uv run alembic revision --autogenerate -m "$(msg)"

downgrade:
	uv run alembic downgrade -1

db-reset:
	uv run alembic downgrade base
	uv run alembic upgrade head

# ── Code quality ─────────────────────────────────────────────────────────────

lint:
	uv run ruff check .

format:
	uv run ruff format .

# ── Tests ────────────────────────────────────────────────────────────────────

test:
	uv run pytest

# ── Help ─────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make run          Start production server (port 8000)"
	@echo "  make dev          Start dev server with auto-reload (port 8000)"
	@echo "  make install      Install / sync dependencies"
	@echo "  make migrate      Apply all pending migrations"
	@echo "  make migration    Generate a new migration  (msg=\"...\" required)"
	@echo "  make downgrade    Roll back the last migration"
	@echo "  make db-reset     Roll back all migrations and re-apply from scratch"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Run ruff formatter"
	@echo "  make test         Run test suite"
	@echo ""
