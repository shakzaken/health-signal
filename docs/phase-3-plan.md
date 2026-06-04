# Phase 3 — Advanced Intelligence Agents

## Where We Are After Phase 2

After Phase 2, the system can:

1. Upload a PDF → parse → chunk → embed → store in Qdrant
2. For blood tests: extract structured markers → save to `lab_results` + `lab_markers` in PostgreSQL
3. Ask a question → supervisor classifies intent → routes to:
   - **Lab Analysis Agent** — fetches marker history from PostgreSQL, reasons over structured numbers
   - **RAG chain** — semantic search over Qdrant, answers general questions

What is still missing:

| Table | Status |
|---|---|
| `documents` | ✅ Filled |
| `lab_results` | ✅ Filled |
| `lab_markers` | ✅ Filled |
| `symptom_entries` | ❌ Empty — models exist, nothing writes to them |
| `supplement_entries` | ❌ Empty — models exist, nothing writes to them |
| `timeline_events` | ❌ Empty — models exist, nothing writes to them |

The system also cannot:
- Reason across different data types at the same time (labs + symptoms + supplements)
- Answer questions about time ranges: "what happened in the last 3 months?"
- Detect patterns: "did my fatigue appear when my Vitamin D was low?"
- Summarize the user's health story over a period

Phase 3 fixes this.

---

## What Phase 3 Builds

### The Core Idea

Phase 2 gave the system structured lab data and a routing brain. Phase 3 fills in the rest of the user's health picture — symptoms, supplements — and adds the intelligence to reason across all of it over time.

Two new agents are the headline features:
- **Pattern Detection Agent** — finds correlations between events across different data types
- **Timeline Agent** — answers "what happened to my health over the past N months?"

Both agents depend on a data foundation that must be built first: symptom and supplement extraction during ingestion, and a timeline event log that records every meaningful health event.

---

## Part 1 — Data Foundation (Backend)

### 1.1 Symptom & Supplement API Endpoints

The backend currently has no routes for reading symptoms or supplements. The ai-agent needs to write extracted data there, and new agents need to query it.

**New backend routes:**

```
POST /symptom-entries          # ai-agent writes after ingestion
GET  /symptom-entries          # agents query symptoms
GET  /symptom-entries?from=YYYY-MM-DD&to=YYYY-MM-DD  # time-filtered

POST /supplement-entries       # ai-agent writes after ingestion  
GET  /supplement-entries       # agents query supplements
GET  /supplement-entries?from=YYYY-MM-DD&to=YYYY-MM-DD  # time-filtered
```

**New backend files:**
- `repositories/symptom_repository.py` — `create_entries()`, `list_all()`, `list_in_range(from_date, to_date)`
- `repositories/supplement_repository.py` — same shape
- `schemas/symptom.py` — `SymptomEntryResponse`
- `schemas/supplement.py` — `SupplementEntryResponse`
- `api/routes/symptoms.py`
- `api/routes/supplements.py`

---

### 1.2 Timeline Event Writer

The `timeline_events` table exists with this schema:

```
event_type      lab_result | symptom | supplement_change | diet_change | note
reference_id    UUID pointing to the source row
reference_table "lab_results" | "symptom_entries" | "supplement_entries"
event_date      date of the health event
summary         one-line plain-text description of the event
```

After Phase 3, a timeline event is written every time:
- A lab result is saved → `event_type=lab_result`, summary = "Blood test: 23 markers, lab_name"
- A symptom entry is saved → `event_type=symptom`, summary = "Symptom: fatigue (moderate)"
- A supplement entry is saved → `event_type=supplement_change`, summary = "Started Vitamin D 2000 IU"

The timeline event writer belongs in `DocumentService` alongside `_save_lab_result()`.

New methods in `DocumentService`:
- `_save_symptoms(document, symptom_data)` — writes `SymptomEntry` rows + timeline events
- `_save_supplements(document, supplement_data)` — writes `SupplementEntry` rows + timeline events
- The existing `_save_lab_result()` is extended to also write a timeline event

**Backend `timeline_service.py`** needs a `create_event()` method (currently likely only has `get_timeline()`).

The `GET /timeline` route already exists and supports `?from=&to=` filters — no change needed there.

---

## Part 2 — AI Agent: Extractors

The ingestion pipeline already extracts lab markers via `LabExtractor`. The same pattern is applied to the other two document types.

### 2.1 SymptomExtractor (`ai-agent/tools/symptom_extractor.py`)

- Input: raw text from a `symptom_note` or `journal` document
- LLM structured output → list of `ExtractedSymptomEntry`
- Each entry: `symptom_name`, `severity` (mild/moderate/severe), `occurred_at`, `notes`

```python
class ExtractedSymptomEntry(BaseModel):
    symptom_name: str
    severity: Optional[str]     # "mild" | "moderate" | "severe"
    occurred_at: str            # ISO date or best-guess from document context
    notes: Optional[str]

class ExtractedSymptoms(BaseModel):
    entries: list[ExtractedSymptomEntry] = []
```

---

### 2.2 SupplementExtractor (`ai-agent/tools/supplement_extractor.py`)

- Input: raw text from a `supplement_list` document
- LLM structured output → list of `ExtractedSupplementEntry`
- Each entry: `name`, `dosage`, `frequency`, `started_at`, `stopped_at`, `notes`

```python
class ExtractedSupplementEntry(BaseModel):
    name: str
    dosage: str
    frequency: str
    started_at: Optional[str]   # ISO date
    stopped_at: Optional[str]   # ISO date
    notes: Optional[str]

class ExtractedSupplements(BaseModel):
    entries: list[ExtractedSupplementEntry] = []
```

---

### 2.3 Ingestion Pipeline Update (`ai-agent/ingestion/pipeline.py`)

The pipeline's `run()` method currently has a special case for `LAB_DOCUMENT_TYPES`. Phase 3 adds two more cases, following the exact same pattern:

```
document_type in {"symptom_note", "journal"}  → SymptomExtractor → return symptom_data
document_type == "supplement_list"            → SupplementExtractor → return supplement_data
```

The ingest response from the ai-agent gains two new optional fields:
```json
{
  "success": true,
  "chunks_stored": 12,
  "lab_result": { ... },       // existing
  "symptom_data": { ... },     // new
  "supplement_data": { ... }   // new
}
```

`DocumentService._trigger_ingestion()` in the backend checks for these new fields and calls the corresponding save methods.

---

## Part 3 — AI Agent: New Tools

### 3.1 Temporal Retriever — date-range filtering in Qdrant

The current `Retriever` accepts `user_id` and `document_type` as filters. Phase 3 adds optional `date_from` / `date_to` parameters.

Qdrant already stores `source_date` as a payload field on every vector. The retriever adds a `range` filter on this field when the dates are provided.

```python
# rag/retriever.py
def retrieve(
    self,
    query: str,
    user_id: str = "default",
    document_type: str | None = None,
    date_from: str | None = None,   # new
    date_to: str | None = None,     # new
) -> list[dict]:
```

---

### 3.2 Tools for the Pattern Detection Agent

These are `@tool`-decorated async functions that the Pattern Detection Agent calls via LangChain tool calling — exactly like the lab analysis tools.

| Tool | Backend call | Purpose |
|---|---|---|
| `fetch_symptoms_in_range(from_date, to_date)` | `GET /symptom-entries?from=&to=` | Get symptoms in a time window |
| `fetch_supplements_in_range(from_date, to_date)` | `GET /supplement-entries?from=&to=` | Get supplement changes in a time window |
| `fetch_lab_markers_in_range(from_date, to_date)` | `GET /lab-results` + filter by date | Get all lab values in a time window |
| `search_documents_in_range(query, from_date, to_date)` | temporal Qdrant retrieval | Semantic search scoped to a time window |

---

### 3.3 Tools for the Timeline Agent

| Tool | Backend call | Purpose |
|---|---|---|
| `fetch_timeline(from_date, to_date)` | `GET /timeline?from=&to=` | Get all timeline events in a window |
| `fetch_timeline_event_detail(event_type, reference_id)` | various `GET` endpoints | Fetch full details of a specific event |

---

## Part 4 — AI Agent: New Agents

### 4.1 Pattern Detection Agent (`ai-agent/agents/pattern_detection.py`)

**Purpose:** Find temporal correlations between different types of health events.

**Routing triggers:** Questions like:
- "Why was I so tired in January?"
- "Did my fatigue correlate with my Vitamin D levels?"
- "What changed around the time my iron was low?"
- "Are there patterns in my health data?"

**How it works:**
1. LLM extracts a time window from the question (e.g., "last winter" → Q4 2024 / Q1 2025)
2. Tool calls: fetch lab markers, symptoms, supplements for that window
3. LLM reasons over the combined data: "Fatigue symptoms (Jan–Feb) overlap with Vitamin D low (Jan test)"
4. Returns observations with explicit "correlation, not causation" framing

**Class shape:**
```python
class PatternDetectionAgent:
    def __init__(self, llm: BaseChatModel, backend_url: str) -> None: ...
    async def analyze(self, question: str, config: RunnableConfig | None = None) -> dict: ...
```

Same tool-calling loop pattern as `LabAnalysisAgent`.

---

### 4.2 Timeline Agent (`ai-agent/agents/timeline.py`)

**Purpose:** Answer "what happened to my health in a given time period?"

**Routing triggers:** Questions like:
- "What happened to my health in the last 6 months?"
- "Give me a summary of my health in 2024"
- "What health events happened around March?"

**How it works:**
1. LLM extracts a time window from the question
2. `fetch_timeline(from_date, to_date)` — gets all events in that window
3. For each significant event, optionally fetch detail (e.g., lab result with markers)
4. LLM synthesizes a chronological narrative in plain language

**Class shape:**
```python
class TimelineAgent:
    def __init__(self, llm: BaseChatModel, backend_url: str) -> None: ...
    async def summarize(self, question: str, config: RunnableConfig | None = None) -> dict: ...
```

---

## Part 5 — Supervisor Enhancement

### 5.1 Updated Routing

The classifier prompt and `RouteDecision` enum gain two new routes:

```python
class RouteDecision(BaseModel):
    route: Literal["lab_analysis", "rag", "pattern_detection", "timeline"]
```

Routing guidance added to the classifier prompt:
- `pattern_detection` — questions about correlations, causes, "why", patterns across time
- `timeline` — questions about health history, summaries of a period, "what happened in X"

### 5.2 Updated Graph

```
            ┌─────────────────┐
            │    classify     │
            └────────┬────────┘
                     │
       ┌─────────────┼─────────────┬──────────────┐
       ▼             ▼             ▼              ▼
  lab_analysis      rag    pattern_detection  timeline
       │             │             │              │
       └─────────────┴─────────────┴──────────────┘
                              │
                             END
```

All four leaf nodes follow the same pattern: call their agent, write `answer` and `sources` back into `AgentState`, edge to `END`.

---

## Part 6 — Gradio UI Enhancements

The Gradio app currently has two tabs: Upload and Query. Phase 3 adds:

### 6.1 Timeline Tab
- Date range pickers (`from` / `to`)
- Calls `GET /timeline?from=&to=`
- Displays events in a formatted chronological list

### 6.2 Lab Markers History Tab
- Dropdown of known marker names (populated from `GET /lab-results`)
- Calls `GET /lab-results/markers/{name}/history`
- Displays values as a simple table with trend indicator (↑ ↓ →)

### 6.3 Symptom & Supplement Tabs (read-only)
- `GET /symptom-entries` → table of recorded symptoms
- `GET /supplement-entries` → table of recorded supplements

---

## Implementation Order

The parts have dependencies. This is the order to build them:

```
1. Backend: symptom + supplement repositories, schemas, routes        (Part 1.1)
2. Backend: timeline event writer in DocumentService                  (Part 1.2)
3. AI agent: SymptomExtractor + SupplementExtractor                   (Part 2.1–2.2)
4. AI agent: ingestion pipeline update + backend _save_* methods      (Part 2.3)
5. AI agent: temporal Retriever                                        (Part 3.1)
6. AI agent: Pattern Detection Agent + tools                          (Parts 3.2, 4.1)
7. AI agent: Timeline Agent + tools                                   (Parts 3.3, 4.2)
8. AI agent: supervisor routing update                                (Part 5)
9. Gradio UI enhancements                                             (Part 6)
```

Steps 1–4 are the data foundation. The agents in steps 6–7 cannot work without real data flowing into the tables. Steps 1–4 should be completed and tested with a real upload before moving to the agents.

---

## What the Tables Look Like After Phase 3

| Table | Status |
|---|---|
| `documents` | ✅ Filled |
| `lab_results` | ✅ Filled |
| `lab_markers` | ✅ Filled |
| `symptom_entries` | ✅ Filled — populated from symptom_note + journal uploads |
| `supplement_entries` | ✅ Filled — populated from supplement_list uploads |
| `timeline_events` | ✅ Filled — one event per lab result, symptom, supplement saved |

---

## Summary

| | Phase 2 | Phase 3 |
|---|---|---|
| Data types | Lab markers only | Labs + symptoms + supplements |
| Time awareness | None | Temporal filtering in Qdrant + timeline events |
| Agents | Lab Analysis + RAG | + Pattern Detection + Timeline |
| Routing | 2 routes | 4 routes |
| Cross-domain reasoning | Not possible | Pattern agent correlates across data types |
| Health narrative | Individual answers | Chronological health story |
