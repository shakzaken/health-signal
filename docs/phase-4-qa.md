# Phase 4 QA — Conversational Memory & Doctor Report

## Prerequisites

Phase 3 test data must already be loaded. If starting fresh, upload the test files first:

| File | Document Type | Source Date |
|---|---|---|
| `test-data/blood_test_2025_06.txt` | `blood_test` | `2025-06-14` |
| `test-data/symptoms_2025.txt` | `journal` | `2025-07-01` |
| `test-data/supplements_2025.txt` | `supplement_list` | `2025-08-03` |
| `test-data/clalit-1.pdf` | `blood_test` | `2026-01-01` |
| `test-data/clalit2.pdf` | `blood_test` | `2026-01-01` |
| `test-data/clalit3.pdf` | `blood_test` | `2026-01-01` |

All six files must be ingested and the following tables must be non-empty before running these tests:
- `GET /lab-results` → at least 2 test dates (June 2025 + January 2026)
- `GET /symptom-entries` → fatigue, brain fog, muscle weakness, cold sensitivity
- `GET /supplement-entries` → Vitamin D, B12, Omega-3, Iron

---

## Part 1 — Conversational Memory

These tests use the **💬 Ask** tab in the Gradio UI. Each numbered group is a single session — do not click "New conversation" between questions within a group. Do click "New conversation" before starting the next group.

---

### CON-1 — Basic follow-up reference

Start a new conversation.

**Turn 1:** `"What was my Vitamin D level in June 2025?"`

✅ Expected:
- 24.1 nmol/L, severely deficient (below 50 nmol/L)
- The lab date June 14, 2025 is mentioned

**Turn 2 (same session):** `"And what was it in January 2026?"`

✅ Expected:
- 74.8 nmol/L — now within normal range
- The agent understands "it" refers to Vitamin D from the previous turn
- Should note the improvement since June

❌ Fail if:
- The agent asks "what do you mean by 'it'?"
- The agent returns data unrelated to Vitamin D
- The agent treats this as a fresh question with no context

---

### CON-2 — Follow-up that changes scope

Start a new conversation.

**Turn 1:** `"Is my iron okay?"`

✅ Expected:
- June 2025: Ferritin 18 ng/mL (low), Serum Iron 52 ug/dL (low), TIBC high
- Indicates iron deficiency

**Turn 2 (same session):** `"What about my Vitamin B12?"`

✅ Expected:
- Agent answers about B12 (not iron again)
- June 2025: 248 pmol/L (normal)
- January 2026: 642 pmol/L (elevated — likely from supplementation)

**Turn 3 (same session):** `"Could the high B12 be caused by the supplement I was taking?"`

✅ Expected:
- Agent connects: started B12 1000 mcg on August 3, 2025
- By January 2026 B12 is elevated → very likely caused by the supplement
- Recommends discussing with doctor whether dose should be adjusted

❌ Fail if:
- Turn 2 answers about iron instead of B12
- Turn 3 cannot connect supplement to lab result without being prompted to look it up

---

### CON-3 — Context across different agents

Start a new conversation.

**Turn 1:** `"What were my main health problems in the summer of 2025?"`

✅ Expected:
- Routes to `pattern_detection` or `timeline`
- Lists: Vitamin D deficiency, iron deficiency, fatigue, brain fog, muscle weakness, cold sensitivity

**Turn 2 (same session):** `"Were those problems resolved by the end of the year?"`

✅ Expected:
- Agent understands "those problems" refers to the issues listed in turn 1
- October/November 2025: symptoms resolved, energy restored
- January 2026: Vitamin D normalized (74.8), B12 elevated from supplementation
- Iron was not retested in January 2026

❌ Fail if:
- The agent asks "which problems are you referring to?"
- The agent gives a completely unrelated answer

---

### CON-4 — Session isolation

This test verifies that two separate conversations do not share context.

**Session A — Turn 1:** `"What is my ferritin level?"`

Note the answer (should mention ~18 ng/mL from June 2025).

Click **"New conversation"**.

**Session B — Turn 1:** `"What were we just talking about?"`

✅ Expected:
- The agent has no context from Session A
- Should say there is no prior conversation or redirect to asking a health question

❌ Fail if:
- The agent mentions ferritin, iron, or anything from Session A

---

### CON-5 — Routing is correct even with history

Start a new conversation.

**Turn 1:** `"What happened to my health in the last year?"` (→ should route to `timeline`)

**Turn 2 (same session):** `"What is my current hemoglobin value?"` (→ should route to `lab_analysis`)

✅ Expected for Turn 2:
- Routes to `lab_analysis` even though the previous turn was a timeline question
- Returns the most recent hemoglobin value from the January 2026 blood test
- Does not confuse the routing just because a different agent was used last time

---

## Part 2 — Doctor Visit Report

These tests use the **📋 Doctor Report** tab in the Gradio UI.

---

### REP-1 — Report is generated and structured

Set the period slider to **90 days** and click **Generate Report**.

✅ Expected — the report must contain all four sections:

1. **ABNORMAL LAB MARKERS** (or equivalent heading) — lists markers outside reference range with their values and normal range
2. **RECENT SYMPTOMS** — lists recorded symptoms from the period with severity/dates
3. **SUPPLEMENT CHANGES** — lists supplement entries from the period
4. **SUGGESTED QUESTIONS FOR YOUR DOCTOR** — at least 3 specific questions derived from the actual data

❌ Fail if:
- The report is empty or returns an error
- Any of the four sections is missing entirely
- The questions are generic (e.g. "How are you feeling?") rather than specific to this user's data

---

### REP-2 — Report reflects the correct time period

**Test A — 365-day period:**
Set the slider to **365 days** and generate.

✅ Expected:
- Includes markers from the June 2025 blood test (Vitamin D 24.1, Ferritin 18, Iron 52)
- Includes symptoms from the summer/autumn 2025 journal entries
- Includes Iron and Vitamin D supplements started August 2025

**Test B — 30-day period:**
Set the slider to **30 days** and generate.

✅ Expected:
- Does NOT include the June 2025 blood test (it's more than 30 days ago)
- "No data available" or similar for sections where nothing falls in the window
- Should still generate without error

❌ Fail if:
- The 30-day report contains data from June 2025
- Either period produces an error instead of a structured report

---

### REP-3 — Report questions are data-specific

Generate a report for **365 days**.

✅ Expected — the suggested questions must reference actual data from this user, for example:
- Something about Vitamin D (it was severely deficient and then normalized)
- Something about B12 (it rose above the reference range)
- Something about iron (deficiency detected, supplement was stopped — was it resolved?)
- Something about the fatigue and whether the lab improvements explain it

❌ Fail if:
- Questions are completely generic and could apply to any patient
- Questions contradict the data (e.g. asking about a high Vitamin D when it was deficient)

---

### REP-4 — Report via supervisor routing

Use the **💬 Ask** tab (start a new conversation).

**Question:** `"Can you prepare a doctor report for me?"`

✅ Expected:
- Routes to `doctor_report` (not `rag`, not `lab_analysis`)
- Returns a structured report similar to what the Report tab generates
- Contains all four expected sections

❌ Fail if:
- Routes to `rag` and returns generic document search results
- Routes to `lab_analysis` and only returns lab values

---

### REP-5 — Report phrasing variants are routed correctly

Start a new conversation for each question. These should all route to `doctor_report`:

| Question | Should route to |
|---|---|
| `"Generate a doctor visit report"` | `doctor_report` |
| `"What should I tell my doctor at my next appointment?"` | `doctor_report` |
| `"Give me a full health summary to show my doctor"` | `doctor_report` |
| `"Prepare me for my appointment"` | `doctor_report` |

❌ Fail if any of these routes to `rag` or `lab_analysis`.

---

## Part 3 — Routing Sanity Checks

These verify that the new `doctor_report` route does not incorrectly capture questions meant for other agents.

| Question | Expected route | Wrong if… |
|---|---|---|
| `"What is my hemoglobin?"` | `lab_analysis` | Generates a full report instead of answering the specific question |
| `"Why was I tired in July 2025?"` | `pattern_detection` | Returns a full report instead of correlating symptoms and lab data |
| `"What happened to my health in 2025?"` | `timeline` | Returns a full report instead of a chronological narrative |
| `"What did my journal say about brain fog?"` | `rag` | Returns structured data or a full report |
| `"Give me a full health report for my doctor"` | `doctor_report` | Routes to any other agent |

---

## Part 4 — Memory + Report Combined

Start a new conversation.

**Turn 1:** `"My Vitamin D was very low in June 2025. Did it improve?"`

✅ Expected:
- Confirms June 2025: 24.1 nmol/L (severely deficient)
- January 2026: 74.8 nmol/L (normal) — significant improvement

**Turn 2 (same session):** `"Given that, what questions should I ask my doctor at my next appointment?"`

✅ Expected:
- Routes to `doctor_report` or `rag`
- References the Vitamin D improvement discussed in Turn 1
- Includes a specific question about Vitamin D (e.g. whether supplementation should continue, what target level to aim for)

❌ Fail if:
- The agent has no memory of the Vitamin D discussion from Turn 1 and gives generic questions

---

## Summary Table

| Test | Feature | Pass criteria |
|---|---|---|
| CON-1 | Follow-up reference ("it") | Agent resolves pronoun from prior turn |
| CON-2 | Scope change across turns | Each turn answers the right topic |
| CON-3 | Cross-agent context | Agent tracks what was discussed across route changes |
| CON-4 | Session isolation | New conversation has zero memory of the previous one |
| CON-5 | Routing with history | Route decision is question-driven, not history-driven |
| REP-1 | Report structure | All four sections present |
| REP-2 | Period filter | Data matches the selected time window |
| REP-3 | Question specificity | Questions reference actual user data |
| REP-4 | Doctor report via chat | Routing works from natural language |
| REP-5 | Routing variants | Multiple phrasings all reach `doctor_report` |
| Routing | No false captures | New route doesn't steal questions from other agents |
| Combined | Memory + report | Report in chat references prior conversation context |
