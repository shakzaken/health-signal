# Health Signal

A personal health data assistant that turns fragmented medical documents into a conversational knowledge base.

Upload your documents — blood tests, lab reports, symptom logs, supplement records, doctor notes — and the system classifies, chunks, and indexes them automatically. You can then ask questions about your health history in plain language: spot trends in your lab markers over time, understand correlations between symptoms and supplements, get a chronological summary of health events, or generate a structured report to bring to a doctor appointment.

The assistant supports Hebrew and English, handles scanned PDFs via vision OCR, and keeps a rolling memory of your conversation so follow-up questions work naturally. Every answer cites the source documents it was drawn from.

## Technologies

| Layer | Stack |
|-------|-------|
| Frontend | React 18, Vite, TypeScript |
| Backend | FastAPI, PostgreSQL, SQLAlchemy (async), Alembic |
| AI Agent | FastAPI, LangGraph, LangChain, OpenAI GPT-4.1-nano |
| Embeddings | FastEmbed — `intfloat/multilingual-e5-large` (1024-dim, CPU) |
| Vector store | Qdrant |
| Auth | JWT (python-jose, bcrypt) |
| Observability | LangSmith |
| Package manager | uv (Python), npm (frontend) |

## Services

The system runs as three independent services:

**Frontend** (`frontend/` · port 5173) — React SPA with three tabs: Upload, Chat, and Doctor Report. The Upload tab accepts PDF and TXT files with an optional source date, shows real-time processing status, and prevents duplicate uploads. The Chat tab streams answers token-by-token and shows source citations for every response. The Doctor Report tab generates a structured visit summary — abnormal labs, recent symptoms, supplement changes, and suggested questions — for a configurable time window. All communication goes through the backend; the AI agent port is never exposed to the browser.

**Backend** (`backend/` · port 8000) — FastAPI service that owns user authentication (email/password, JWT), all structured health data (PostgreSQL via SQLAlchemy async + Alembic migrations), and uploaded file storage. It validates every request before forwarding to the AI agent, minting a scoped token so the AI agent can call backend data endpoints on behalf of the user. Structured data — lab markers, symptom entries, supplement entries, timeline events — is written here after each ingestion and read back by the AI agent during query time.

**AI Agent** (`ai-agent/` · port 8001) — FastAPI service responsible for two workflows. During ingestion it runs a pipeline that parses the document (with GPT-4.1-nano vision OCR as fallback for scanned PDFs), classifies its type, chunks the text, embeds it with `multilingual-e5-large`, runs a type-specific structured extractor (lab, symptom, or supplement), and writes vectors to Qdrant. During query time a LangGraph supervisor classifies the question and routes it to one of five handlers: `LabAnalysisAgent` for marker trends, `PatternDetectionAgent` for cross-data correlations, `TimelineAgent` for chronological summaries, `DoctorReportAgent` for structured visit prep, or `QueryChain` for general RAG search. Non-English queries use dual retrieval — the original query plus an English translation — so Hebrew questions can match English documents and vice versa.

## Getting Started

Each service has its own `.env` file. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full list of environment variables, and [`PRODUCT.md`](PRODUCT.md) for a feature overview.
