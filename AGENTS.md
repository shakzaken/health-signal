# AGENTS.md

## Purpose

This document defines the preferred engineering conventions for this project. The goal is to keep the codebase consistent, simple, and easy to maintain.

---

## Python / FastAPI

### Architecture

* Use **Pydantic** for application models, request models, and response models.
* Use **object-oriented style** for **services**, **repositories**, and **AI/ML pipeline classes** across all services.
* Use **repositories** for interacting with the database.
* Use **services** for interacting with infrastructure components such as **cache** and **queues** (for example Redis or RabbitMQ), and for coordinating business flows when needed.
* Keep **FastAPI routes** as regular functions, not class-based routes.
* Use **async-first FastAPI design** unless a task explicitly states otherwise.
* Prefer **async libraries** for database, queue, HTTP, and storage integrations when building FastAPI services.
* Prefer `async def` for FastAPI route handlers, service methods, and repository methods that perform I/O.
* If a synchronous library must be used, document the reason clearly and keep the blocking boundary explicit.

### Backend service (`backend/`)

* Use **SQLAlchemy** (with asyncpg) directly for database access — do not use SQLModel as an ORM.
* Define database tables using SQLAlchemy's `mapped_column` / `DeclarativeBase` style.
* Use **Pydantic** models separately for API request and response schemas — keep DB models and API schemas in separate files.
* Schema is managed exclusively by **Alembic** migrations. Never call `create_all()` or any equivalent at application startup.
* Use **asyncpg** as the async PostgreSQL driver via SQLAlchemy's async engine.
* Use **psycopg2** only for Alembic migrations (sync context required).

### AI agent service (`ai-agent/`)

* Use **object-oriented style** for all pipeline and RAG components — every logical component must be a class, not a module-level function.
* Examples: `IngestionPipeline`, `DocumentParser`, `Chunker`, `Embedder`, `Retriever`, `QueryChain`, `QdrantWriter`.
* Inject dependencies explicitly through constructors — avoid module-level singletons except for expensive shared resources (e.g. the embedding model).
* Expose shared singletons via FastAPI dependency providers in `api/deps.py`.

### Recommended structure

* Keep route handlers thin.
* Use type hints everywhere.
* Put database access logic inside repositories.
* Do not put business logic in repositories.
* Put external system access logic inside services.
* Keep business logic out of route handlers as much as possible.
* Inject dependencies explicitly through FastAPI dependencies.

### Validation and schemas

* Use Pydantic models for validation at the API boundary.
* Keep request and response schemas explicit.
* Avoid passing raw dictionaries between layers when a typed model makes the contract clearer.

### Code style

* Prefer clear names over clever abstractions.
* Keep functions and methods focused on one responsibility.
* Avoid unnecessary inheritance.
* Prefer composition over deep class hierarchies.

### Environment and packaging

* Use **uv** as the Python package manager for Python services.
* Keep a separate Python environment per service.
* Use `backend/.venv` for the backend service and `ai-agent/.venv` for the AI agent service.
* Keep Python dependencies scoped to each service's own `pyproject.toml`.
* Do not rely on a shared root Python virtual environment across services.

---

## React

* Use **Vite** as the frontend build tool.
* Use **TypeScript**.
* Prefer functional components.
* Keep components small and focused.
* Extract reusable UI logic into hooks only when it improves clarity.
* Avoid unnecessary global state.

---

## Planning and implementation

* **Do not start implementing unless the user explicitly says to.**
* During planning phases, only produce plans, diagrams, documents, and analysis.
* Do not write code, create files, or scaffold anything unless directly instructed.
* Do not add eager phrases like "Ready to start Phase X" or "Shall we begin implementation?" — wait to be told.

---

## General principles

* **Do not over-engineer.**
* **Keep it simple.**
* Test every task that you do.
* Prefer readability over cleverness.
* Make the smallest reasonable change that solves the problem.
* Keep modules cohesive and easy to navigate.
* Avoid introducing new libraries unless there is a clear reason.
* Follow the existing project structure and naming conventions.
* Write code that is easy to debug and easy to remove if requirements change.

---


