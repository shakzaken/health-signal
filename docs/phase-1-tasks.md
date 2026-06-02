# Phase 1 — Tasks & Steps

## Overview

Tasks are grouped by area and ordered by dependency — each group should be completed before
moving to the next. Within a group, tasks can be done in parallel where noted.

---

## Group 1 — Project Scaffolding

### Task 1.1 — Create folder structure
- Create `backend/`, `ai-agent/`, `gradio-app/` folders
- Create subdirectory structure inside each as defined in the plan
- Create empty `__init__.py` files to make packages importable

### Task 1.2 — Initialize backend service
- Run `uv init` inside `backend/`
- Add dependencies: `fastapi`, `uvicorn`, `sqlmodel`, `asyncpg`, `alembic`, `pydantic-settings`, `python-multipart`, `httpx`
- Create `backend/core/config.py` with settings loaded from `.env`

### Task 1.3 — Initialize ai-agent service
- Run `uv init` inside `ai-agent/`
- Add dependencies: `fastapi`, `uvicorn`, `langchain`, `langchain-community`, `langgraph`, `langsmith`, `qdrant-client`, `fastembed`, `pymupdf`, `openai`, `pydantic-settings`, `httpx`, `sqlmodel`, `asyncpg`
- Create `ai-agent/core/config.py` with settings loaded from `.env`

### Task 1.4 — Initialize gradio app
- Run `uv init` inside `gradio-app/`
- Add dependencies: `gradio`, `httpx`
- Create `gradio-app/core/config.py` for backend and ai-agent base URLs

### Task 1.5 — Create root `.env` file
- Define all environment variables:
  - `DATABASE_URL`
  - `QDRANT_HOST`, `QDRANT_PORT`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY` (used only for GPT-4o mini OCR fallback)
  - `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`
  - `BACKEND_URL`
  - `AI_AGENT_URL`
  - `FILE_STORAGE_PATH`

---

## Group 2 — PostgreSQL Setup

### Task 2.1 — Install and start PostgreSQL locally
- Install via Homebrew: `brew install postgresql`
- Start the service: `brew services start postgresql`
- Create the database: `createdb healthsignal`

### Task 2.2 — Define SQLModel models
Create one file per model group in `backend/models/`:
- `document.py` — `Document`, `DocumentType` enum, `ProcessingStatus` enum
- `lab_result.py` — `LabResult`, `LabMarker`, `MarkerStatus` enum
- `symptom.py` — `SymptomEntry`, `SymptomSeverity` enum
- `supplement.py` — `SupplementEntry`
- `timeline.py` — `TimelineEvent`, `EventType` enum

### Task 2.3 — Set up database connection
- Create `backend/db/session.py` with async SQLAlchemy engine and session factory
- Create `backend/db/base.py` that imports all models (required by Alembic)

### Task 2.4 — Set up Alembic
- Run `alembic init` inside `backend/`
- Configure `alembic.ini` and `env.py` to use the async engine and SQLModel metadata
- Generate initial migration: `alembic revision --autogenerate -m "initial schema"`
- Apply migration: `alembic upgrade head`
- Verify all tables exist in the database

---

## Group 3 — Qdrant Setup

### Task 3.1 — Install and start Qdrant locally
- Install via Homebrew: `brew install qdrant` or download the binary from qdrant.io
- Start Qdrant: run the binary or `brew services start qdrant`
- Verify it is running at `http://localhost:6333`

### Task 3.2 — Create Qdrant collection
- Create `ai-agent/rag/qdrant_client.py` — wrapper around the Qdrant client
- On service startup, create the `health_documents` collection if it does not exist
- Configure collection for FastEmbed's vector size (384 dimensions for `BAAI/bge-small-en-v1.5`)
- Define the metadata payload fields: `document_id`, `user_id`, `document_type`, `source_date`, `filename`, `chunk_index`

---

## Group 4 — Backend Repositories & Services

> Can be done in parallel with Group 3.

### Task 4.1 — Implement repositories
Create one repository per model group in `backend/repositories/`:
- `document_repository.py` — create, get by id, list all, update status
- `lab_result_repository.py` — create result, create markers, get result with markers, get marker history by name
- `symptom_repository.py` — create, list by date range
- `supplement_repository.py` — create, list active
- `timeline_repository.py` — insert event, list events with date filter

### Task 4.2 — Implement services
Create services in `backend/services/`:
- `document_service.py`
  - Save uploaded file to `FILE_STORAGE_PATH`
  - Create document record in DB with status `pending`
  - Call ai-agent `POST /ingest` via httpx
  - Update document status based on response
- `timeline_service.py`
  - Query `timeline_events` table with optional date filters
  - Return unified sorted list of events

### Task 4.3 — Implement API routes
Create route files in `backend/api/routes/`:
- `documents.py` — `POST /documents/upload`, `GET /documents`, `GET /documents/{id}`
- `lab_results.py` — `GET /lab-results`, `GET /lab-results/{id}`, `GET /markers/{name}/history`
- `timeline.py` — `GET /timeline` with `?from=&to=` query params
- `health.py` — `GET /health`

### Task 4.4 — Wire up backend main.py
- Create FastAPI app instance
- Include all routers
- Set up DB session lifespan

---

## Group 5 — Ingestion Pipeline (Deterministic Program)

### Task 5.1 — Implement document parser
Create `ai-agent/ingestion/parser.py`:
- Accept a file path and document type
- If PDF: extract text using PyMuPDF (`fitz`)
- If plain text: read directly
- Validate extracted text using `is_meaningful_text()` heuristic (no LLM needed):
  - `len(text.strip()) > 100`
  - `len(text.split()) > 20`
  - `alphabetic characters / total characters > 0.6`
- If any check fails, trigger OCR fallback:
  - Convert each PDF page to an image using PyMuPDF
  - Send images to GPT-4o mini Vision API with prompt: "Extract all text from this medical document"
  - Return the OCR-extracted text
- Return extracted raw text string

Create `ai-agent/ingestion/vision_extractor.py`:
- Wrap the OpenAI Vision API call
- Accept a list of page images (base64 encoded)
- Call GPT-4o mini with vision input
- Return extracted text string

### Task 5.2 — Implement text chunker
Create `ai-agent/ingestion/chunker.py`:
- Use LangChain `RecursiveCharacterTextSplitter`
- Configure chunk size and overlap suitable for health documents (chunk_size=500, overlap=50)
- Return list of text chunks with their index

### Task 5.3 — Implement embedder
Create `ai-agent/ingestion/embedder.py`:
- Wrap FastEmbed using the Qdrant client's built-in FastEmbed support
- Model: `BAAI/bge-small-en-v1.5`
- Accept list of text chunks, return list of vectors

### Task 5.4 — Implement Qdrant writer
Create `ai-agent/rag/writer.py`:
- Accept chunks + vectors + metadata (document_id, user_id, document_type, source_date, filename)
- Write all points to the `health_documents` collection in Qdrant

### Task 5.5 — Implement ingestion orchestrator
Create `ai-agent/ingestion/pipeline.py`:
- Orchestrate the full pipeline: parse → update raw_text in Postgres → chunk → embed → write to Qdrant → update status
- Handle errors and update document status to `failed` if any step fails
- Wire in LangSmith tracing so every step is visible

### Task 5.6 — Implement ingest API route
Create `ai-agent/api/routes/ingest.py`:
- `POST /ingest` — accepts document_id, file_path, document_type, source_date
- Calls the ingestion pipeline
- Returns success or error with details

---

## Group 6 — AI Agent RAG Query

### Task 6.1 — Implement Qdrant retriever
Create `ai-agent/rag/retriever.py`:
- Accept a query string, user_id, and optional filters (document_type, date range)
- Embed the query using FastEmbed
- Search Qdrant with `user_id` filter applied first
- Return top-k relevant chunks with their metadata

### Task 6.2 — Implement query chain
Create `ai-agent/rag/query_chain.py`:
- Use LangChain to build a retrieval + LLM chain
- Combine retrieved Qdrant chunks as context
- Call Claude via Anthropic API through LangChain
- Return the final answer
- Wire in LangSmith tracing

### Task 6.3 — Implement query API route
Create `ai-agent/api/routes/query.py`:
- `POST /query` — accepts a question string and optional filters
- Calls the retriever and query chain
- Returns the answer and the source chunks used

---

## Group 7 — LangSmith Setup

> Should be done before Group 5 and 6 so all traces are captured from the start.

### Task 7.1 — Configure LangSmith
- Create a LangSmith project at smith.langchain.com
- Add `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT` to `.env`
- Set `LANGCHAIN_TRACING_V2=true` in environment
- Verify traces appear in the LangSmith dashboard after the first ingestion run

---

## Group 8 — Gradio App

### Task 8.1 — Build upload tab
In `gradio-app/app.py`:
- File upload component (accepts PDF and text files)
- Document type dropdown
- Source date input
- Submit button calling `POST /documents/upload` on backend
- Status output showing processing state

### Task 8.2 — Build query tab
In `gradio-app/app.py`:
- Text input for the question
- Submit button calling `POST /query` on ai-agent
- Output area showing the answer
- Expandable section showing the source chunks used

---

## Group 9 — End-to-End Test

### Task 9.1 — Prepare test document
- Create or find a sample blood test PDF (or plain text mock)
- Ensure it contains multiple lab markers with values and reference ranges

### Task 9.2 — Run full flow
1. Start PostgreSQL
2. Start Qdrant
3. Start backend: `uv run uvicorn main:app` in `backend/`
4. Start ai-agent: `uv run uvicorn main:app` in `ai-agent/`
5. Start Gradio: `uv run python app.py` in `gradio-app/`
6. Upload the test document via Gradio
7. Verify document record appears in PostgreSQL with status `completed`
8. Verify chunks appear in Qdrant `health_documents` collection
9. Ask a question about the document via Gradio
10. Verify a relevant answer is returned
11. Verify the full trace appears in LangSmith

### Task 9.3 — Verify backend endpoints
- Test all endpoints via FastAPI `/docs` Swagger UI
- Verify `/timeline` returns events
- Verify `/markers/{name}/history` returns values

---

## Completion Criteria

Phase 1 is complete when:

- [ ] All five services start without errors
- [ ] A PDF can be uploaded and reaches `completed` status in PostgreSQL
- [ ] Document chunks are stored and searchable in Qdrant
- [ ] A natural language question returns a relevant answer via Gradio
- [ ] All backend endpoints return correct data via Swagger
- [ ] Every ingestion and query run is visible as a trace in LangSmith
