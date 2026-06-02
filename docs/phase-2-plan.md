# Phase 2 — Core Agent Graph

## Where We Are After Phase 1

After Phase 1, the system works like this:

1. You upload a PDF
2. The vision model reads it and extracts the raw text
3. The text is split into chunks and stored in Qdrant as vectors
4. PostgreSQL stores only the document metadata (filename, type, status) — the health data tables (`lab_results`, `lab_markers`, etc.) exist but are all **empty**
5. You ask a question → the system finds relevant chunks in Qdrant → GPT reads them and answers

The limitation: the system treats your lab results as a text document, not as data. It can't answer "is my hemoglobin trending down over the last 3 tests?" because hemoglobin isn't stored as a value — it's buried inside a text chunk.

---

## What Phase 2 Builds

### The Core Idea

After Phase 1, we have a smart search engine. After Phase 2, we have an agent that actually understands what's in your documents and can reason over it.

Two things make this possible:
1. **Structured extraction** — after ingestion, an agent reads the raw text and saves the actual health values into PostgreSQL
2. **A supervisor** — instead of every question going straight to the RAG chain, a supervisor reads your intent and routes to the right specialist

---

### 1. Structured Extraction During Ingestion

**Currently:**
```
Upload PDF → vision reads it → raw text → chunks → Qdrant
                                         ↓
                               PostgreSQL: filename, status only
```

**After Phase 2:**
```
Upload PDF → vision reads it → raw text → chunks → Qdrant
                                    ↓
                          LLM extracts structured data
                                    ↓
                          PostgreSQL: lab_results, lab_markers
                          (name, value, unit, reference range, status)
```

Concretely — when you upload a blood test, the agent reads:
```
Hemoglobin: 14.2 g/dL  (reference: 12.0–16.0)
```
And saves to PostgreSQL:
```
name:           "Hemoglobin"
value:          14.2
unit:           "g/dL"
reference_low:  12.0
reference_high: 16.0
status:         "normal"
test_date:      2024-03-15
document_id:    <link to the document>
```

This is what makes trend analysis possible. Now the system can query: "give me all hemoglobin values ordered by date" and actually get numbers back.

---

### 2. Lab Analysis Agent

With structured markers in PostgreSQL, a dedicated agent can:
- Pull the full history of any marker across all your uploads
- Compare each value to its reference range
- Detect trends (going up, going down, stable)
- Give you a plain-language explanation: *"Your hemoglobin has dropped from 14.2 in March to 12.1 in June — that's a downward trend, still within normal range but worth watching."*

This is not possible today because the values aren't stored as numbers — they're inside text chunks.

---

### 3. Supervisor (Orchestrator)

Right now every question goes directly to the RAG chain. Phase 2 adds a supervisor at the front that classifies your intent:

```
Your question
      ↓
  Supervisor
      ↓
┌─────────────────────────────────┐
│                                 │
▼                                 ▼
Lab Analysis Agent          RAG Chain (fallback)
(structured data questions) (general / open questions)
```

Examples:
- "What's my hemoglobin trend?" → Lab Analysis Agent (uses PostgreSQL data)
- "What did my doctor say about my diet?" → RAG Chain (searches Qdrant)
- "Upload this PDF" → Ingestion Agent

Without the supervisor, every question hits RAG regardless of what it's asking. With the supervisor, each question goes to the agent best equipped to answer it.

---

### 4. Tools

Small focused utilities that agents call internally:

- **Reference Range Lookup** — given a marker name, returns what's considered normal. Agents use this to classify values as normal / high / low without having to infer it from the document.
- **Lab Value Extractor** — given raw text from a lab PDF, returns a structured list of `LabMarker` objects. Used by the ingestion agent during extraction.

---

## What the Tables Look Like After Phase 2

**Before Phase 2 (today):**

| Table | Status |
|---|---|
| `documents` | ✅ Filled — every upload is here |
| `lab_results` | ❌ Empty |
| `lab_markers` | ❌ Empty |
| `symptom_entries` | ❌ Empty |
| `supplement_entries` | ❌ Empty |
| `timeline_events` | ❌ Empty |

**After Phase 2:**

| Table | Status |
|---|---|
| `documents` | ✅ Filled |
| `lab_results` | ✅ Filled — one row per blood test |
| `lab_markers` | ✅ Filled — one row per marker per test |
| `symptom_entries` | ❌ Still empty (Phase 3) |
| `supplement_entries` | ❌ Still empty (Phase 3) |
| `timeline_events` | ❌ Still empty (Phase 3) |

---

## Summary

| | Phase 1 | Phase 2 |
|---|---|---|
| Storage | Qdrant only (text chunks) | Qdrant + PostgreSQL (structured values) |
| Routing | Every question → RAG chain | Supervisor routes to the right agent |
| Lab data | Buried in text | Extracted, typed, queryable |
| Trend analysis | Not possible | Possible — values are numbers now |
| Architecture | RAG pipeline | Multi-agent graph (LangGraph) |
