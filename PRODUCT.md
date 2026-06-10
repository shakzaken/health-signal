# PRODUCT.md — Health Signal

## 1. Product Summary

**Health Signal** is a personal health data assistant that lets users upload their medical documents and then have a natural conversation about their health history.

The core problem it solves: health data is fragmented across paper lab reports, PDF results from clinics, handwritten symptom diaries, and supplement lists. Health Signal centralises all of it, understands the content automatically, and lets users query it in plain language — including in Hebrew.

**Who it is for:** individuals who actively track their own health and want to understand trends, prepare for doctor visits, or simply ask questions like "was my iron level improving over the last year?" without manually scanning documents.

**Main value:** convert a pile of health documents into a searchable, conversational knowledge base — with AI that reasons across all data types together rather than treating each document in isolation.

---

## 2. Target Users

### Primary: The Self-Tracking Patient

- Receives regular blood tests (e.g. from Clalit or other HMOs)
- Keeps symptom journals or supplement logs
- Wants to spot trends over months without manually comparing PDFs
- May communicate in Hebrew

**Features that help them:** document upload with automatic classification, AI chat for trend questions, doctor report generator.

### Secondary: Pre-Appointment Preparer

- Has an upcoming doctor visit and wants to arrive with organised data
- Needs to summarise what changed since the last visit
- Wants a list of specific questions to ask

**Features that help them:** Doctor visit report (covers abnormal labs, symptoms, supplement changes, and suggested questions).

---

## 3. Main Product Capabilities

| Capability | Description |
|------------|-------------|
| **Document upload & indexing** | Upload a PDF or TXT file; the system classifies, chunks, embeds, and indexes it automatically |
| **Conversational health assistant** | Ask questions about your health data in natural language; answers stream in real time |
| **Intelligent routing** | Questions are classified and routed to the right reasoning mode (lab analysis, pattern detection, timeline, report, or general search) |
| **Doctor visit report** | Generate a structured report of abnormal labs, symptoms, and supplement changes for a configurable time window |
| **Multi-language support** | Questions and answers work in Hebrew and English; documents in either language are retrieved correctly |
| **Session memory** | Conversation history persists across page reloads; older turns are summarised automatically to keep context relevant |
| **Source attribution** | Every AI answer shows which documents the answer came from, with document type, date, and a relevance score |
| **Duplicate prevention** | Re-uploading the same file is silently rejected — the system detects duplicates by content hash |

---

## 4. Feature List

### Authentication

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| User registration | Email + password sign-up | Implemented | No email verification |
| Login | Email + password | Implemented | Returns a JWT stored in localStorage |
| Logout | Clears token and session state | Implemented | — |
| Session persistence | Token survives page refresh | Implemented | — |
| Password reset | — | Not implemented | — |

### Document Upload

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| File upload (drag-and-drop) | Upload PDF or TXT by dragging or file picker | Implemented | Max 20 MB per UI label; not enforced on backend |
| Source date | Optional date field to tag when the document is from | Implemented | Falls back to upload date |
| Automatic classification | System detects document type (blood test, lab report, symptom note, etc.) | Implemented | LLM-based; can be overridden if type is known |
| Processing status display | Shows Completed / Processing / Failed after upload | Implemented | — |
| Document status checker | Look up processing status by document ID | Implemented | Manual lookup by ID only; no document list view |
| Duplicate detection | Identical file re-uploads are rejected (409) | Implemented | Per user, based on SHA-256 hash |
| Vision OCR fallback | Scanned or image-only PDFs are processed via GPT-4 vision | Implemented | Activated when pdfplumber extracts no text |
| Document list view | Browse previously uploaded documents | Not implemented | Backend route exists; no UI |

### AI Chat

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Streaming answers | Tokens appear as they are generated | Implemented | SSE (Server-Sent Events) |
| Source citations | Each answer shows which documents were used | Implemented | Shows filename, type, date, similarity score |
| Session history sidebar | Previous conversations listed; click to restore | Implemented | Stored in localStorage only |
| New conversation | Start a fresh session | Implemented | — |
| Conversation memory | History is persisted server-side and injected into each request | Implemented | Last 6 messages verbatim + rolling summary |
| Automatic summarisation | Old messages compressed by LLM when session exceeds 14 messages | Implemented | Fire-and-forget; transparent to user |
| Multi-language queries | Hebrew and English queries both retrieve Hebrew and English documents | Implemented | Dual retrieval with English translation |
| Follow-up question support | Context from prior turns affects route classification and answers | Implemented | Last 4 messages included in classification |

### Intelligent Query Routing (5 modes)

| Route | When it activates | What it does |
|-------|-------------------|--------------|
| **Lab analysis** | Questions about specific markers, values, or trends | Fetches full lab history; analyses trends and flags abnormal values |
| **Pattern detection** | Correlations across data types; "why was I tired in January?" | Queries lab, symptom, and Qdrant data; cross-table reasoning |
| **Timeline** | Chronological summaries; "what supplements am I taking now?" | Queries timeline and supplement entries; ordered view |
| **Doctor report** | "Generate a report" or "prepare me for my appointment" | Fetches all three data sources and generates a structured report |
| **RAG (general)** | Document content; diet notes; anything else | Semantic search across all uploaded documents |

### Doctor Visit Report

| Feature | Description | Status | Notes |
|---------|-------------|--------|-------|
| Report generation | LLM-generated summary of abnormal labs, symptoms, supplement changes | Implemented | — |
| Time period selection | 30 days / 90 days / 6 months / 1 year | Implemented | — |
| Suggested questions | 3–6 doctor questions derived from the user's actual data | Implemented | — |
| Copy to clipboard | One-click copy of full report text | Implemented | — |
| Download as PDF | Download button present in UI | Partially implemented | UI button exists; actual PDF generation needs verification |
| Conversation-aware | If called from chat, uses conversation context to improve relevance | Implemented | — |

---

## 5. Inputs and Outputs

### What users can input

| Input | Format | Where |
|-------|--------|-------|
| Health documents | PDF, TXT (up to 20 MB per UI) | Upload tab |
| Optional source date | Date field | Upload tab |
| Natural language questions | Text (Hebrew or English) | Chat tab |
| Report period | 30 / 90 / 180 / 365 days | Doctor report tab |

### Document types the system understands

| Type | What it is | How it is processed |
|------|------------|---------------------|
| `blood_test` | Blood test results PDF | Structured extraction of markers, values, reference ranges |
| `lab_report` | Clinical lab report | Same as blood_test |
| `symptom_note` | Symptom diary entry | Structured extraction of symptom name, severity, date |
| `journal` | General health journal | Same as symptom_note |
| `supplement_list` | Supplement log | Structured extraction of name, dosage, frequency, start/stop dates |
| `diet_note` | Diet or nutrition note | Indexed for search only; no structured extraction |
| `doctor_summary` | Doctor visit note | Indexed for search only; no structured extraction |

### What the system produces

| Output | Where it appears | Description |
|--------|-----------------|-------------|
| Streaming answer | Chat tab | Plain-language response to the question |
| Source citations | Chat tab (source panel) | Which documents and chunks were used, with similarity scores |
| Doctor visit report | Doctor report tab | Structured markdown report with 4 sections + suggested questions |
| Processing confirmation | Upload tab | Document ID, detected type, and status after upload |
| Conversation history | Layout sidebar | Session titles derived from first user message |
