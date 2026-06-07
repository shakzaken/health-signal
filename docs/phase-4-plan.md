# Phase 4 — Doctor Visit Report & Conversational Memory

## Where We Are After Phase 3

After Phase 3, the system can:

| Capability | Status |
|---|---|
| Upload any document (PDF or text) | ✅ |
| Auto-classify document type | ✅ |
| Extract structured data (labs, symptoms, supplements) | ✅ |
| Store everything in PostgreSQL | ✅ |
| Semantic search in Qdrant | ✅ |
| Answer lab questions (LabAnalysisAgent) | ✅ |
| Find correlations across data (PatternDetectionAgent) | ✅ |
| Summarize health over a period (TimelineAgent) | ✅ |
| General document Q&A (RAG) | ✅ |
| Full LangSmith tracing | ✅ |
| Gradio UI: Upload + Ask tabs | ✅ |

**What the system still cannot do:**

- Generate a structured report to bring to a doctor appointment
- Remember what was said earlier in a conversation ("what did I just ask?")
- Answer multi-turn questions with context ("and how does that compare to now?")
- Synthesize ALL health data into one overall narrative

Phase 4 fixes this.

---

## What Phase 4 Builds

### The Core Idea

Phase 3 gave the system intelligence across all data types. Phase 4 makes that intelligence **useful and interactive**:

1. **Doctor Visit Report** — a structured, printable report generated from all your data, with suggested questions to ask your doctor
2. **Conversational Memory** — the agent remembers the conversation so follow-up questions work naturally

---

## Part 1 — Doctor Visit Report Agent

### What it does

The user clicks "Generate Report" and receives a structured document like:

```
HEALTH REPORT — June 2026

ABNORMAL LAB MARKERS
  • Vitamin B12: 152 pg/mL (low — reference: 200–900) — trending down since Jan
  • Ferritin: 8 ng/mL (low — reference: 12–150) — consistently low

SYMPTOMS (last 3 months)
  • Fatigue — moderate — reported 4 times
  • Brain fog — mild — reported 2 times
  • Headache — mild — reported 1 time

SUPPLEMENT CHANGES (last 3 months)
  • Started Vitamin D 2000 IU (March 2026)
  • Stopped Iron supplement (April 2026)

SUGGESTED QUESTIONS FOR YOUR DOCTOR
  1. My B12 has dropped from 280 to 152 in 6 months — should we investigate why?
  2. My ferritin has been below range in all 3 of my last tests — is IV iron appropriate?
  3. Could the fatigue and brain fog be linked to the low B12 and ferritin?
```

### Why this is architecturally different

All current agents answer a single question and stop. The Doctor Report Agent is a **sequential pipeline** — it must gather data from multiple sources, then synthesize everything into one structured output.

The supervisor currently routes to exactly ONE agent. The Doctor Report is a new route that triggers a different kind of agent — one that runs multiple data-fetching steps, then calls an LLM to produce a final document.

### Agent design

The `DoctorReportAgent` is a LangGraph with **deterministic sequential nodes**, not a tool-calling loop:

```
START
  │
  ▼
fetch_data          ← parallel: fetch recent lab abnormalities + symptoms + supplements
  │
  ▼
generate_questions  ← LLM: generate doctor questions from the fetched data
  │
  ▼
compile_report      ← LLM: write the final structured report
  │
  ▼
END
```

**Why not a tool-calling loop?** The Doctor Report follows a fixed structure — we always want the same three data sections and always produce the same report format. Using deterministic nodes (like the ingestion pipeline) is simpler and more predictable than an open-ended ReAct loop.

**Why LangGraph and not just sequential code?** LangGraph gives us:
- Full LangSmith trace visibility: each node appears as a named span
- State flows naturally between nodes without passing arguments everywhere
- Easy to extend (add a "trend analysis" node later) without restructuring

### New files

**`ai-agent/agents/doctor_report.py`** — the Doctor Report Agent

```python
class DoctorReportState(TypedDict):
    user_id: str
    period_days: int         # how many days back to look (default 90)
    lab_summary: str         # output of fetch_data node
    symptom_summary: str
    supplement_summary: str
    questions: list[str]     # output of generate_questions node
    report: str              # final compiled report

class DoctorReportAgent:
    def __init__(self, llm: BaseChatModel, backend_url: str) -> None: ...
    async def generate(self, user_id: str, period_days: int = 90) -> dict: ...
```

### New backend endpoint

The Doctor Report is triggered from a dedicated UI button, not a chat question. It gets its own route on the ai-agent:

```
POST /report/generate
Body: { "user_id": "default", "period_days": 90 }
Response: { "report": "...", "questions": [...] }
```

### Supervisor update

The supervisor's classifier gains a fifth route: `doctor_report`.

Routing trigger: questions like "generate a report", "prepare me for my doctor visit", "give me a health summary to show my doctor".

```python
class RouteDecision(BaseModel):
    route: Literal["lab_analysis", "pattern_detection", "timeline", "rag", "doctor_report"]
```

The `_run_doctor_report` supervisor node calls `DoctorReportAgent.generate()` and formats the result as the answer.

---

## Part 2 — Conversational Memory

### The problem

Right now, every question is completely stateless. The agent sees only the current message. Follow-up questions like these are impossible:

> "What was my B12 last month?"  
> → "It was 180."  
> "And how does that compare to the month before?"  ← the agent has no memory of the first answer

### What we add

**Conversation history** flows with every query. The agent sees the full conversation, not just the latest message. This is stored in Postgres so history survives browser refreshes and new sessions.

### New Postgres table: `conversations`

```
id          UUID (PK)
session_id  UUID — groups messages in one conversation
user_id     TEXT
role        "user" | "assistant"
content     TEXT — the message content
created_at  TIMESTAMP
```

### New backend routes

```
GET  /conversations/{session_id}       # load history for a session
POST /conversations/{session_id}       # append a message
```

### The problem with sending all history

A naive implementation sends the full conversation history on every query. After a long session this leads to:
- High token cost on every request
- Eventually hitting the LLM's context window limit and hard-failing

### Solution: Summary + recent window

We maintain two things per session:

1. A **rolling summary** — a short LLM-written paragraph describing the older conversation ("The user has been investigating low B12 and iron trends, and asking whether fatigue could be related")
2. The **last N messages verbatim** (e.g. last 6 turns) — enough for the agent to follow immediate context

On every query, the LLM receives: `[summary] + [last N messages] + [new question]`. Total size is bounded regardless of how long the conversation runs.

The summary is regenerated whenever the session grows past a threshold (e.g. every 10 new turns). The oldest messages beyond the window are compressed into an updated summary paragraph and dropped from the verbatim list.

The summary compression step runs as a lightweight async background task **after** the agent responds — it never adds latency to the user-facing query.

### How it flows

1. Gradio UI generates a `session_id` when the user first opens the Ask tab (or loads a previous session)
2. On each question, the backend loads `session_summary + last N messages` from the DB
3. The query is sent to the ai-agent with `{ "question": "...", "session_id": "...", "summary": "...", "recent_history": [...] }`
4. The supervisor's `AgentState` gains `summary` and `recent_history` fields
5. The classifier and each sub-agent include both in the LLM prompt so prior context is visible
6. After the agent responds, the backend appends the new turn and triggers the background summarization check

### AgentState update

```python
class AgentState(TypedDict):
    question: str
    user_id: str
    session_id: str                  # NEW
    summary: str                     # NEW — rolling summary of older turns
    recent_history: list[dict]       # NEW — last N turns verbatim [{role, content}, ...]
    document_type: str | None
    answer: str
    sources: list[dict]
    route: str
```

### New DB tables

**`conversations`** — individual message log:
```
id          UUID
session_id  UUID
user_id     TEXT
role        "user" | "assistant"
content     TEXT
created_at  TIMESTAMP
```

**`conversation_sessions`** — one row per session, holds the rolling summary:
```
session_id  UUID (PK)
user_id     TEXT
summary     TEXT       ← LLM-generated summary of older turns, updated periodically
updated_at  TIMESTAMP
```

### New backend files

- `models/conversation.py` — SQLAlchemy models for both tables
- `repositories/conversation_repository.py` — `get_session()`, `append_message()`, `update_summary()`, `get_recent_messages(n)`
- `schemas/conversation.py` — `ConversationMessage`, `ConversationSession`
- `api/routes/conversations.py`
- Alembic migration for both tables

---

## Part 3 — Gradio UI Updates

### 3.1 Report Tab (new)

A new "Doctor Report" tab:
- A "Generate Report" button
- Optional: date range (defaults to last 90 days)
- Displays the rendered report in a text box
- Shows suggested doctor questions as a separate list

### 3.2 Ask Tab — conversation history

The Ask tab gains:
- A `session_id` persisted in the UI state (auto-generated on first load)
- The full conversation displayed as a back-and-forth chat (not a single Q&A box)
- A "New conversation" button to reset the session

---

## Implementation Order

```
1. Backend: conversations table + Alembic migration             (Part 2 — DB)
2. Backend: conversation repository + routes                    (Part 2 — API)
3. AI agent: AgentState + supervisor updated to accept history  (Part 2 — Agent)
4. Gradio: Ask tab updated with session_id + chat history UI   (Part 3.2)
5. AI agent: DoctorReportAgent (fetch_data + compile nodes)    (Part 1 — Agent)
6. AI agent: /report/generate endpoint                         (Part 1 — API)
7. AI agent: supervisor gains doctor_report route              (Part 1 — Supervisor)
8. Gradio: Doctor Report tab                                   (Part 3.1)
```

Steps 1–4 (conversational memory) are independent of steps 5–8 (doctor report). Memory is more foundational and should be built first — the Doctor Report can also use it if the user has asked prior questions.

---

## What Changes vs Stays the Same

| | Phase 3 | Phase 4 |
|---|---|---|
| Conversation style | Single Q&A (stateless) | Multi-turn chat with memory |
| History persistence | None | Stored in Postgres per session |
| Report generation | Not possible | Structured doctor visit report |
| Supervisor routes | 4 (lab, pattern, timeline, rag) | 5 (+ doctor_report) |
| Agent graph style | ReAct tool-calling loops | + sequential pipeline (Doctor Report) |
| Gradio tabs | 2 (Upload, Ask) | 3 (Upload, Ask, Report) |
| New DB tables | — | `conversations` |
| New backend routes | — | `/conversations`, `/report/generate` |

---

## Summary

Phase 4 has two independent features:

**Conversational Memory** — the simpler of the two. It is mostly infrastructure: a new DB table, two backend routes, and threading `history` through the existing agent pipeline. The payoff is immediate and noticeable — the agent goes from amnesiac to actually conversational.

**Doctor Visit Report** — the most user-facing feature in the project. It is the first time the system chains multiple data sources into a single structured output instead of answering a single question. It requires a new agent type (sequential pipeline graph) and a new UI tab. This is the feature that makes the product feel complete.
