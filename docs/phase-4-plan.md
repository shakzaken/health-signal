# Phase 4 — Doctor Visit Report & UX Improvements

## Requirements collected so far

---

### Automatic document type classification

**Problem:**
Users are currently required to manually select a document type (blood_test, journal, supplement_list, etc.) when uploading a file. This is error-prone and puts unnecessary burden on the user — they uploaded supplements_2025.txt as "blood_test" and got no supplement data extracted as a result.

**Solution:**
Add a `DocumentClassifier` step at the start of the ingestion pipeline. If the user does not provide a document type, the pipeline reads the parsed text and classifies it automatically using LLM structured output.

**Flow:**
```
User uploads file (document_type optional)
        ↓
  Parse raw text
        ↓
  Classify document type  ← new LLM step (runs only if type not provided)
        ↓
  Chunk → Embed → Qdrant
        ↓
  Run appropriate extractor based on classified type
```

**What changes:**
- `document_type` becomes optional on the backend upload form
- New `DocumentClassifier` in `ai-agent/tools/document_classifier.py` — LLM structured output returning one of: `blood_test`, `lab_report`, `symptom_note`, `supplement_list`, `diet_note`, `doctor_summary`, `journal`
- `IngestionPipeline.run()` — if `document_type` is None, run classifier after parsing
- `IngestResponse` — include detected `document_type` in response
- `DocumentService._trigger_ingestion()` — save detected type back to the `documents` table
- UI — document type field becomes optional / hidden by default

**What stays the same:** all extractors, routing, and DB writes are unchanged.

---

## Planned features (from high-level-plan.md Phase 4)

- Doctor Visit Report Agent — generates a structured appointment-prep report: abnormal markers, trend summary, symptom timeline, suggested questions
- Tool: Question Generator — LLM tool that produces medically-relevant questions the user should ask their doctor
- Conversational Q&A — multi-turn conversation with context across messages
- Health Summary Agent — synthesizes output from all agents into one narrative
- Memory layer — persist conversation context across sessions
