# Flow 2 — Conversational Query (Chat)

> **Services** · Frontend `React :5173` · Backend `FastAPI + PostgreSQL :8000` · AI-Agent `FastAPI + Qdrant :8001`

A user question travels through the backend auth proxy, loads conversation history, is classified by a LangGraph supervisor, and is routed to one of five sub-agents. The answer streams back as Server-Sent Events; the turn is then persisted and optionally compressed into a rolling summary.

---

## Pipeline Diagram

```mermaid
flowchart TD
    classDef fe     fill:#E0F2F1,stroke:#00897B,stroke-width:2px,color:#004D40,font-weight:bold
    classDef be     fill:#E8EAF6,stroke:#3949AB,stroke-width:2px,color:#1A237E,font-weight:bold
    classDef ai     fill:#FFFBEB,stroke:#D97706,stroke-width:2px,color:#78350F,font-weight:bold
    classDef store  fill:#F3E8FF,stroke:#7C3AED,stroke-width:2px,color:#4C1D95
    classDef decide fill:#FFF7ED,stroke:#EA580C,stroke-width:2px,color:#7C2D12
    classDef err    fill:#FEE2E2,stroke:#DC2626,stroke-width:2px,color:#7F1D1D
    classDef done   fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D

    START(["User sends a question"]):::fe

    subgraph FE[Frontend - React :5173]
        FE1["ChatPage\nPOST /ai/query/stream"]:::fe
    end

    subgraph BE_PROXY[Backend - Auth and Proxy :8000]
        BP1["JWT validation\nget_current_user"]:::be
        BP2["Mint ai-agent token\nproxy SSE stream\nPOST /query/stream"]:::be
    end

    subgraph MEM_LOAD[ConversationMemory - Load]
        ML1["ConversationMemory.load\nGET /conversations/session_id"]:::be
        ML2[("PostgreSQL\nrolling summary\nlast 6 messages")]:::store
    end

    subgraph CLASSIFY[Supervisor - Classify]
        CL1["LLM structured output\nRouteDecision\nuses summary + last 4 messages"]:::ai
        ROUTE{"route?"}:::decide
    end

    subgraph AGENTS[Structured Agents - LangGraph ReAct]
        AG1["LabAnalysisAgent\nfetch_lab_results\nget_marker_history"]:::ai
        AG2["PatternDetectionAgent\nlab + symptom + rag tools\ncross-table correlation"]:::ai
        AG3["TimelineAgent\ntimeline + supplement tools\nchronological summary"]:::ai
        AG4["DoctorReportAgent\nsequential pipeline\nall data sources"]:::ai
    end

    subgraph RAG[QueryChain - RAG]
        R1["Retriever.retrieve\nembed question\nquery Qdrant primary\nuser_id filter"]:::ai
        RLANG{"is English?"}:::decide
        R2["Translate to English\nLLM call"]:::ai
        R3["Retriever.retrieve\nQdrant secondary\nenglish query"]:::ai
        R4["Merge by score\ndeduplicate\ntop-5 chunks"]:::ai
        RCTX{"chunks\nfound?"}:::decide
        R5["Build prompt\nsystem + summary + history\n+ context chunks\n+ language enforcement"]:::ai
        RNONE(["No relevant documents\nin uploaded files"]):::err
    end

    STREAM["LLM response\nstreamed as SSE tokens"]:::ai

    subgraph MEM_SAVE[ConversationMemory - Save]
        MS1["POST /conversations/session_id/messages\nuser turn and assistant answer"]:::be
        MS2{"total gt 14\nmessages?"}:::decide
        MS3["Summarize async\nfire-and-forget\nDoctorReportAgent.summarize\nPUT /summary"]:::ai
    end

    DONE(["Answer streamed to user\nsources displayed in UI"]):::done

    START   --> FE1
    FE1     -->|POST /ai/query/stream| BP1
    BP1     --> BP2
    BP2     -->|POST /query/stream| ML1
    ML1     --> ML2
    ML2     -->|summary + last 6 turns| CL1
    CL1     --> ROUTE

    ROUTE   -->|lab_analysis| AG1
    ROUTE   -->|pattern_detection| AG2
    ROUTE   -->|timeline| AG3
    ROUTE   -->|doctor_report| AG4
    ROUTE   -->|rag| R1

    AG1     -->|answer + sources| STREAM
    AG2     -->|answer + sources| STREAM
    AG3     -->|answer + sources| STREAM
    AG4     -->|report text| STREAM

    R1      --> RLANG
    RLANG   -->|yes - primary only| RCTX
    RLANG   -->|no| R2
    R2      --> R3
    R3      --> R4
    R4      --> RCTX
    RCTX    -->|no chunks| RNONE
    RCTX    -->|chunks found| R5
    RNONE   --> STREAM
    R5      --> STREAM

    STREAM  --> MS1
    MS1     --> MS2
    MS2     -->|no| DONE
    MS2     -->|yes| MS3
    MS3     --> DONE
```

---

## Steps at a Glance

| # | Step | Service · Component | Output |
|---|------|---------------------|--------|
| 1 | User submits question | Frontend `ChatPage` | `POST /ai/query/stream` with `session_id` |
| 2 | Auth + proxy | Backend `get_current_user` → proxy route | JWT validated; new short-lived token minted for ai-agent |
| 3 | Load history | AI-Agent `ConversationMemory.load` | Rolling summary + last 6 messages from PostgreSQL |
| 4 | Classify | AI-Agent `Supervisor._classify` | `RouteDecision` — one of 5 routes |
| 5a | Lab analysis | `LabAnalysisAgent` ReAct loop | Calls `fetch_lab_results` / `get_marker_history` → Backend |
| 5b | Pattern detection | `PatternDetectionAgent` ReAct loop | Calls lab + symptom + rag tools; cross-table correlation |
| 5c | Timeline | `TimelineAgent` ReAct loop | Calls timeline + supplement tools → Backend |
| 5d | Doctor report | `DoctorReportAgent` sequential pipeline | Aggregates all data; generates structured report |
| 5e | RAG | `QueryChain` — embed → retrieve → prompt → LLM | Semantic Qdrant search; optional dual retrieval for Hebrew |
| 6 | Stream answer | LLM → SSE → Backend proxy → Frontend | `{"token": "..."}` events; final `{"sources": [...]}` event |
| 7 | Save turn | `ConversationMemory.save_turn` | 2 messages written to PostgreSQL (user + assistant) |
| 8 | Maybe summarize | `ConversationMemory.maybe_summarize` | If total > 14 messages → async summarization, fire-and-forget |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Backend as auth proxy** | The ai-agent port stays private; all auth logic lives in one place — the backend validates the user JWT and mints a scoped token for the ai-agent |
| **Rolling summary + last 6 verbatim** | Older turns are compressed into a summary (via LLM) while recent turns stay verbatim — gives the classifier follow-up context without growing the prompt unboundedly |
| **Summarization at 14 messages** | 14 messages ≈ 7 back-and-forth turns — long enough for context to dilute relevance more than it adds value; threshold is a single constant |
| **Async fire-and-forget summarization** | Summarization is an LLM call that doesn't block the response — the user sees the answer immediately; the summary is ready for the next turn |
| **Classify with history** | The last 4 raw messages are included in the classification prompt so follow-up questions ("what about my iron?") are routed correctly instead of always defaulting to RAG |
| **Fallback to RAG on classifier error** | Any exception in structured output parsing routes to `rag` — the safest general-purpose handler |
| **Dual retrieval for Hebrew queries** | The corpus mixes Hebrew Clalit PDFs and English journals; translating the query and searching twice then merging by score ensures cross-language hits |
| **Language enforcement in prompt** | A `CRITICAL` system message immediately before the question overrides any language bleed from Hebrew document chunks in the context |
| **SSE token streaming** | Each LLM token is forwarded as a `data: {"token": "..."}` event; the final event carries `sources` — the frontend can render progressively without waiting for the full answer |

---

## Route Classification

| Route | When | Sub-agent / Handler | Data sources |
|-------|------|---------------------|--------------|
| `lab_analysis` | Questions about specific markers, values, reference ranges, trends for one marker | `LabAnalysisAgent` ReAct | `GET /lab-results` — PostgreSQL `lab_results` + `lab_markers` |
| `pattern_detection` | Correlations across data types, causes, symptom/energy changes over time | `PatternDetectionAgent` ReAct | lab + symptom + rag tools — PostgreSQL + Qdrant |
| `timeline` | Chronological summaries, when events started/stopped, current supplement status | `TimelineAgent` ReAct | `GET /timeline` + `GET /supplements` — PostgreSQL |
| `doctor_report` | Structured report for a doctor appointment, full health summary | `DoctorReportAgent` sequential | All PostgreSQL tables + Qdrant |
| `rag` | General questions, document content, diet, doctor notes, anything else | `QueryChain` RAG | Qdrant `health_documents` collection |
