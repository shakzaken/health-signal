# Phase 1 — Foundation & Infrastructure Plan

## Goal

Get the full skeleton of the system running end-to-end before any AI intelligence is added.
By the end of Phase 1, a user can upload a health document, have it parsed and stored in both
PostgreSQL and Qdrant, and ask a basic question that retrieves relevant content.

---

## Services Overview

| Service | Purpose | How it runs |
|---------|---------|-------------|
| PostgreSQL | Structured health data (markers, symptoms, supplements, timeline) | Local process (Homebrew) |
| Qdrant | Vector DB for semantic search over unstructured document text | Local process (Homebrew or binary) |
| Backend | FastAPI — file uploads, structured data API, business logic | `uv run` in `backend/` |
| AI Agent | FastAPI — ingestion pipeline, RAG queries, LangSmith tracing | `uv run` in `ai-agent/` |
| Gradio | Demo UI — file upload tab + query tab | `uv run` in `gradio-app/` |

FastEmbed runs **in-process** inside the AI Agent service. No separate process or port needed.

---

## Project Structure

```
health-signal/
├── backend/
│   ├── api/
│   │   └── routes/
│   │       ├── documents.py
│   │       ├── lab_results.py
│   │       ├── timeline.py
│   │       └── health.py
│   ├── models/             # SQLModel table definitions
│   ├── schemas/            # Pydantic request/response models
│   ├── repositories/       # DB access layer (one per table group)
│   ├── services/           # Business logic
│   ├── db/                 # DB connection, Alembic migrations
│   ├── core/               # Config, settings, env vars
│   └── main.py
├── ai-agent/
│   ├── ingestion/          # Document parsing + chunking + embedding pipeline
│   ├── rag/                # Qdrant retrieval logic
│   ├── agents/             # LangGraph agents (Phase 2+, scaffolded here)
│   ├── tools/              # LangChain tools (Phase 2+, scaffolded here)
│   ├── api/
│   │   └── routes/
│   │       ├── ingest.py
│   │       ├── query.py
│   │       └── health.py
│   ├── core/               # Config, settings, env vars
│   └── main.py
├── gradio-app/
│   └── app.py              # Gradio UI — upload tab + query tab
└── docs/
```

---

## PostgreSQL Schema

### documents
Stores every uploaded file and its processing state.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| filename | VARCHAR | Original file name |
| file_path | VARCHAR | Path on local filesystem |
| document_type | ENUM | `blood_test`, `lab_report`, `symptom_note`, `supplement_list`, `diet_note`, `doctor_summary`, `journal` |
| source_date | DATE | When the document is from (e.g. test date) |
| uploaded_at | TIMESTAMP | When it was uploaded |
| processing_status | ENUM | `pending`, `processing`, `completed`, `failed` |
| raw_text | TEXT | Full extracted text — used for full-document retrieval without RAG |

### lab_results
One row per lab test session (e.g. one blood test panel).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| document_id | UUID (FK → documents) | |
| test_date | DATE | |
| lab_name | VARCHAR | Optional — name of the lab/clinic |
| created_at | TIMESTAMP | |

### lab_markers
One row per individual marker within a lab result.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| lab_result_id | UUID (FK → lab_results) | |
| name | VARCHAR | e.g. "Vitamin B12", "TSH", "Ferritin" |
| value | FLOAT | |
| unit | VARCHAR | e.g. "pg/mL", "mIU/L" |
| reference_low | FLOAT | Nullable |
| reference_high | FLOAT | Nullable |
| status | ENUM | `normal`, `low`, `high`, `borderline_low`, `borderline_high` |
| created_at | TIMESTAMP | |

### symptom_entries
Symptoms logged manually or extracted from uploaded documents.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| document_id | UUID (FK → documents, nullable) | Null if entered manually |
| symptom_name | VARCHAR | |
| severity | ENUM | `mild`, `moderate`, `severe` |
| occurred_at | DATE | |
| notes | TEXT | Nullable |
| created_at | TIMESTAMP | |

### supplement_entries
Supplements tracked over time.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| document_id | UUID (FK → documents, nullable) | |
| name | VARCHAR | e.g. "Vitamin D3" |
| dosage | VARCHAR | e.g. "2000 IU" |
| frequency | VARCHAR | e.g. "daily" |
| started_at | DATE | Nullable |
| stopped_at | DATE | Nullable |
| notes | TEXT | Nullable |
| created_at | TIMESTAMP | |

### timeline_events
Unified chronological view across all data types.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID (PK) | |
| event_type | ENUM | `lab_result`, `symptom`, `supplement_change`, `diet_change`, `note` |
| reference_id | UUID | FK to the relevant record in its own table |
| reference_table | VARCHAR | Which table the reference_id points to |
| event_date | DATE | |
| summary | TEXT | Short human-readable description |
| created_at | TIMESTAMP | |

---

## Retrieval Architecture — Two Tiers

Health data is retrieved through two separate paths that are always combined before reaching the LLM.

### Tier 1 — Structured retrieval (PostgreSQL)
Used for all structured health data: lab markers, supplements, symptoms, timeline events.
Retrieved via direct SQL queries — deterministic, always complete, no semantic drift.

### Tier 2 — Semantic retrieval (Qdrant RAG)
Used for unstructured free-text content: doctor notes, journal entries, lab commentary.
Chunks are filtered by `user_id` (metadata payload) first, then ranked by semantic similarity.
RAG is solving the **context window problem** — not the user scoping problem.

```
User query
    │
    ├──► SQL query (structured data)     → markers, timeline, supplements
    │
    └──► Qdrant RAG (filtered by user)  → relevant text chunks from documents
                    │
                    ▼
            Merged context → LLM → Answer
```

---

## Qdrant Setup

### Collection: `health_documents`
Stores chunked text from all uploaded documents.

| Metadata field | Purpose |
|---------------|---------|
| `document_id` | Link back to the PostgreSQL documents record |
| `user_id` | Always filtered on — ensures user isolation |
| `document_type` | Allows filtering by type (e.g. only doctor notes) |
| `source_date` | Enables date-range filtering for temporal queries |
| `filename` | For display purposes |
| `chunk_index` | Position of this chunk within the original document |

### Embedding model
**FastEmbed** — `BAAI/bge-small-en-v1.5` (~130MB, runs in-process inside ai-agent, no GPU needed).
Model is downloaded on first run and cached in `~/.cache/fastembed/`.

### OCR fallback
**GPT-4o mini** (OpenAI Vision API) — used only when PyMuPDF fails to extract meaningful text
(i.e. scanned/image-based PDFs). Cheap (~$0.0003 per page) and capable enough for text extraction.
Requires an `OPENAI_API_KEY` in the environment.

---

## Document Ingestion Pipeline

> This is a **deterministic Python pipeline**, not an AI agent flow.
> Steps are fixed and sequential — no LLM reasoning or decision-making is involved.
> The only LLM call is the OCR fallback, which is a simple if/else condition, not agent logic.

```
File upload received by backend
        │
        ▼
File saved to local filesystem
        │
        ▼
Document record created in PostgreSQL (status: pending)
        │
        ▼
Backend calls ai-agent POST /ingest
        │
        ▼
[pipeline.py] Parse document (PyMuPDF for PDF, plain text otherwise)
        │
        ├── Text meaningful? (len > 100, words > 20, alpha ratio > 0.6) ──► Continue ✅
        │
        └── Empty or too short? ──► OCR fallback
                                          │
                                          ▼
                                  Convert PDF pages to images (PyMuPDF)
                                          │
                                          ▼
                                  Send images to GPT-4o mini Vision API
                                  (single LLM call — not an agent)
                                          │
                                          ▼
                                  Use extracted text ✅
        │
        ▼
[pipeline.py] Update document.raw_text in PostgreSQL
        │
        ▼
[pipeline.py] Chunk text (LangChain RecursiveCharacterTextSplitter)
        │
        ▼
[pipeline.py] Embed chunks (FastEmbed)
        │
        ▼
[pipeline.py] Store vectors in Qdrant with metadata
        │
        ▼
AI Agent: update document.processing_status → completed
        │
        ▼
Return success to backend
```

---

## Backend API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload file, save to disk, trigger ingestion |
| `GET` | `/documents` | List all uploaded documents |
| `GET` | `/documents/{id}` | Get single document + processing status |
| `GET` | `/lab-results` | List all lab results |
| `GET` | `/lab-results/{id}` | Get one result with all its markers |
| `GET` | `/markers/{name}/history` | All historical values for a marker (e.g. B12), ordered by date |
| `GET` | `/timeline` | Full timeline, supports `?from=&to=` date filters |
| `GET` | `/health` | Service health check |

---

## AI Agent API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Parse document, embed, store in Qdrant, update Postgres |
| `POST` | `/query` | RAG query — returns relevant chunks filtered by user |
| `GET` | `/health` | Service health check |

---

## Gradio App (Phase 1 UI)

A single `app.py` with two tabs:

**Tab 1 — Upload**
- Drag and drop file input
- Document type selector
- Source date picker
- Upload button → calls `POST /documents/upload` on backend
- Status display (pending → processing → completed)

**Tab 2 — Ask**
- Text input for the question
- Submit button → calls `POST /query` on ai-agent
- Displays retrieved context chunks and LLM answer

---

## LangSmith Tracing

Wired into the ai-agent from day one. Every call to the ingestion pipeline and every RAG query
is traced automatically. This gives full visibility into:
- Document parsing steps
- Chunking and embedding
- Qdrant retrieval results
- LLM calls and responses

---

## Package Management

Each service has its own isolated Python environment:

| Service | Location |
|---------|----------|
| Backend | `backend/pyproject.toml` + `backend/.venv` |
| AI Agent | `ai-agent/pyproject.toml` + `ai-agent/.venv` |
| Gradio | `gradio-app/pyproject.toml` + `gradio-app/.venv` |

All managed with `uv`.
