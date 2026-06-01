# HealthSignal — High-Level Implementation Plan

## Architecture Overview

```
User Input / Uploads
        │
        ▼
┌─────────────────────────────────────────────┐
│          Orchestrator Agent (LangGraph)      │
│     Routes intent → specialized sub-agents  │
└─────┬──────┬──────┬──────┬──────────────────┘
      │      │      │      │
      ▼      ▼      ▼      ▼
 Ingestion  Lab   Pattern Timeline   Doctor
 Pipeline Analysis  Agent  Agent    Report
(program)  Agent                     Agent
      │      │      │      │          │
      └──────┴──────┴──────┴──────────┘
                     │
              ┌──────┴──────┐
              │   Qdrant    │  ◄── RAG layer (all agents query here)
              │  Vector DB  │
              └─────────────┘
                     │
              ┌──────┴──────┐
              │  PostgreSQL │  ◄── Structured health data
              └─────────────┘
                     │
              LangSmith Tracing & Observability
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent graph | LangGraph |
| LLM chains & tools | LangChain |
| Observability | LangSmith |
| Vector / semantic search | Qdrant |
| Structured data | PostgreSQL |
| LLM | Claude (Anthropic) |
| OCR fallback (scanned PDFs) | GPT-4o mini (OpenAI Vision API) |
| Document parsing | PyMuPDF + LangChain document loaders |
| Structured output | Pydantic + LangChain structured output chains |
| Backend API | FastAPI |
| Frontend | React / Next.js (later phases) |

---

## Project Structure

```
health-signal/
├── frontend/          # React/Next.js (later phases)
├── backend/           # FastAPI + PostgreSQL
│   ├── api/
│   ├── models/
│   ├── services/
│   └── db/
├── ai-agent/          # LangGraph + LangChain + Qdrant
│   ├── agents/
│   ├── tools/
│   ├── rag/
│   ├── chains/
│   └── api/          # Thin FastAPI layer exposing the agent
├── docker-compose.yml # Postgres + Qdrant + both services
└── docs/
```

The `ai-agent` is a standalone service with its own FastAPI layer. The backend calls it over HTTP — a clean boundary between business logic and AI logic.

---

## Phase 1 — Foundation & Infrastructure

**Goal:** Get the skeleton running end-to-end before any intelligence is added.

| Task | Description |
|------|-------------|
| Project scaffolding | Folder structure, dependency management, env config for all services |
| Data models | Define core schemas: `HealthDocument`, `LabResult`, `LabMarker`, `SymptomEntry`, `SupplementEntry`, `TimelineEvent` |
| PostgreSQL setup | Docker container, tables for all core models, SQLModel/SQLAlchemy ORM |
| Qdrant setup | Docker container, collections per data type, abstracted behind a `VectorStore` interface |
| LangSmith setup | Project + API key wired in; all chains traced from day one |
| Document ingestion pipeline | Upload → parse (PDF/text/OCR) → chunk → embed → store in Qdrant |
| Basic RAG chain | LangChain retrieval chain over Qdrant — the backbone all agents will use |
| Docker Compose | Single `docker-compose.yml` spinning up Postgres, Qdrant, backend, and ai-agent |

---

## Phase 2 — Core Agent Graph (LangGraph)

**Goal:** Build the multi-agent supervisor graph with the two most critical agents.

| Task | Description |
|------|-------------|
| Orchestrator / Supervisor node | LangGraph `StateGraph` with a supervisor that classifies intent and routes to the right sub-agent |
| Shared agent state | Define `HealthSignalState` — conversation history, active user context, retrieved documents, tool outputs |
| Document Ingestion Agent | Triggered on upload — extracts structured data (dates, marker names, values, units, reference ranges) from lab PDFs using LLM + structured output |
| Lab Analysis Agent | Retrieves marker history from Qdrant, compares to reference ranges, generates plain-language explanation with trend direction |
| Tool: Reference Range Lookup | Static + LLM-augmented tool returning normal ranges for common lab markers |
| Tool: Lab Value Extractor | Parses raw lab text → structured `LabMarker` objects |
| LangSmith tracing | Full trace visibility on every agent call and tool use |

---

## Phase 3 — Advanced Intelligence Agents

**Goal:** Cross-document reasoning — the agents that make the product genuinely impressive.

| Task | Description |
|------|-------------|
| Pattern Detection Agent | Correlates events across document types over time (e.g. low Vitamin D in Jan + fatigue symptoms in Jan/Feb) using RAG + temporal reasoning |
| Timeline Agent | Builds a chronological `TimelineEvent` list from all user data; answers "what happened in the last 6 months?" |
| Tool: Temporal Query | Filters Qdrant by date range — enables time-aware RAG |
| Tool: Cross-Marker Correlation | Identifies which markers move together or against each other across tests |
| Supplement / Symptom Tracker Agent | Tracks supplement intake changes alongside lab and symptom data; flags possible correlations |
| LangGraph conditional edges | Orchestrator dynamically decides whether to invoke one agent or chain multiple agents for complex queries |

---

## Phase 4 — Doctor Visit Report & Conversational Q&A

**Goal:** The two user-facing flagship features that tie everything together.

| Task | Description |
|------|-------------|
| Doctor Report Agent | Generates a structured appointment-prep report: abnormal markers, trend summary, symptom timeline, suggested questions |
| Tool: Question Generator | LLM tool that produces medically-relevant questions the user should ask their doctor based on their data |
| Conversational Q&A interface | LangGraph loop that handles multi-turn conversation, maintains context, and routes follow-up questions through the graph |
| Health Summary Agent | Synthesizes output from all other agents into one narrative: "What is going on with my health over time?" |
| Memory layer | Persist user health context across sessions (LangChain message history + structured user profile in Postgres) |

---

## Phase 5 — Frontend

**Goal:** A clean UI that makes the agentic AI system accessible and demo-ready.

| Task | Description |
|------|-------------|
| Project setup | Next.js + Tailwind CSS |
| Document upload UI | Drag-and-drop file upload, upload status, document list |
| Health Timeline view | Chronological view of all health events |
| Lab Results view | Marker values with trend indicators, reference range visualization |
| Chat interface | Conversational Q&A with the agent, streamed responses |
| Doctor Report view | Rendered report with export option |
| Dashboard | Summary cards: recent changes, flagged markers, upcoming items |

---

## Phase 6 — Observability, Evaluation & Polish

**Goal:** Make the system trustworthy, debuggable, and impressive to demonstrate.

| Task | Description |
|------|-------------|
| LangSmith dashboards | Trace every agent call, tool use, and RAG retrieval — full reasoning visibility |
| LangSmith evaluations | Eval datasets for: lab extraction accuracy, pattern detection quality, report coherence |
| Guardrails | Safety layer — no diagnostic claims; all outputs framed as observations and questions |
| Demo dataset | Realistic synthetic health data (blood tests, symptoms, supplements) across 6–12 months |
| End-to-end testing | Upload → ingest → query → report full flow tests |

---

## Impressive Agentic AI Elements

1. **Multi-agent supervision with dynamic routing** — the graph decides which combination of agents to invoke based on user intent
2. **Temporal RAG** — retrieval is date-aware, enabling trend and timeline queries across time
3. **Cross-modal correlation** — the pattern agent reasons across labs, symptoms, and supplements simultaneously
4. **Agentic report generation** — the doctor report agent chains multiple sub-agents in sequence to produce a coherent output
5. **Full LangSmith observability** — every reasoning step is traceable and evaluatable
6. **Structured health data extraction** — unstructured PDFs → typed, queryable health records automatically
7. **Separate AI microservice** — the agent graph is a standalone deployable service, mirroring real production AI architecture
