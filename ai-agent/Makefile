.PHONY: run dev install lint format test help

# ── Dev server ───────────────────────────────────────────────────────────────

run:
	uv run uvicorn main:app --host 0.0.0.0 --port 8001

dev:
	uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# ── Dependencies ─────────────────────────────────────────────────────────────

install:
	uv sync

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
	@echo "  make run          Start production server (port 8001)"
	@echo "  make dev          Start dev server with auto-reload (port 8001)"
	@echo "  make install      Install / sync dependencies"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Run ruff formatter"
	@echo "  make test         Run test suite"
	@echo ""
