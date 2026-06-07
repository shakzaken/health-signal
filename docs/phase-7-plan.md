# Phase 7 — Auth, Multi-User, Streaming & PDF Export

## Overview

Phase 7 takes the product from a single-user personal tool to a proper multi-user application. It adds the four features that are required before this can be used by anyone other than the developer:

1. **Authentication** — secure login so only authorised users can access the app
2. **Multiple users** — each user sees only their own data, sessions, and history
3. **Streaming responses** — the AI answer appears word by word instead of after a long wait
4. **PDF export** — the doctor report can be downloaded as a PDF to bring to an appointment

---

## Feature 1 — Authentication

### What it does

Users log in with email + password before they can access any part of the app. All API routes are protected — unauthenticated requests are rejected.

### Approach

- **JWT-based auth** — on login, the backend issues a signed JWT access token
- The React frontend stores the token in memory (not localStorage, for security) and attaches it to every API request as a `Authorization: Bearer <token>` header
- The backend validates the token on every protected route using a FastAPI dependency

### New backend pieces

- `models/user.py` — `User` table: `id`, `email`, `hashed_password`, `created_at`
- `repositories/user_repository.py` — `get_by_email()`, `create()`
- `api/routes/auth.py` — `POST /auth/register`, `POST /auth/login` (returns JWT)
- `core/security.py` — password hashing (bcrypt), JWT sign/verify
- FastAPI dependency `get_current_user` — validates JWT and injects the user into every protected route
- Alembic migration for the `users` table

### React changes

- Login page (email + password form)
- Token stored in React state / context, attached to every `fetch` call
- Redirect to login if a request returns 401
- Logout button clears the token

---

## Feature 2 — Multiple Users

### What it does

Right now `user_id` is hardcoded to `"default"` everywhere. In Phase 7 it becomes the authenticated user's actual ID. Each user's documents, lab results, symptoms, supplements, conversations, and sessions are isolated — one user cannot see another's data.

### What changes

**Backend:**
- Every table that has `user_id TEXT` already has the column — it just needs to be populated from the JWT instead of hardcoded
- Every repository query gains a `user_id` filter (most already have it, but it was never enforced)
- The `get_current_user` dependency provides the real `user_id` to all routes automatically

**AI agent:**
- `user_id` flows from the JWT through the query request body — the supervisor and all sub-agents already accept `user_id`, they just need to receive the real value
- Qdrant payloads already store `user_id` per chunk — retrieval is already filtered by it

**React:**
- After login, the user's ID is decoded from the JWT and attached to every API call
- No UI change needed — the data isolation is invisible to the user

### Migration

Existing data under `user_id = "default"` stays as-is and can be reassigned manually if needed.

---

## Feature 3 — Streaming Responses

### What it does

Instead of waiting 5–10 seconds for the full AI answer to arrive, the response streams word by word into the chat window as the LLM generates it.

### Approach

**AI agent side:**
- The `/query` endpoint gains a streaming variant: `POST /query/stream`
- Uses FastAPI's `StreamingResponse` with Server-Sent Events (SSE)
- LangChain's `.astream()` is used instead of `.ainvoke()` — each token chunk is sent as an SSE event
- The supervisor and sub-agents support streaming by passing chunks up through the graph

**React side:**
- The `useChat` hook reads the SSE stream using the browser's `EventSource` API (or `fetch` with `ReadableStream`)
- Each incoming chunk is appended to the current assistant message in real time
- A blinking cursor shows while the stream is in progress
- When the stream ends, sources are sent as a final SSE event

### What does NOT stream

- The Doctor Report — it is a structured document and benefits from being displayed all at once
- The lab/pattern/timeline agents do most of their work via tool calls before the final answer — streaming only applies to the final answer generation step

---

## Feature 4 — PDF Export

### What it does

A "Download as PDF" button on the Doctor Report page generates and downloads a formatted PDF of the report — ready to print and bring to a doctor appointment.

### Approach

**Option A — Frontend-only (preferred):**
- Use a library like `jsPDF` or `react-pdf` to generate the PDF entirely in the browser from the report text
- No backend changes needed
- Simple: the report is plain text with clear section headers — easy to format

**Option B — Backend:**
- The backend generates the PDF server-side (e.g. using `WeasyPrint` or `reportlab`) and returns it as a file download
- More control over formatting, but adds a Python dependency and a new endpoint

**Recommendation:** Start with Option A. The report is structured text — a frontend PDF library handles it cleanly without adding backend complexity.

### PDF contents

- Header: "Health Report — [date range]"
- Four sections matching the report structure: Abnormal Lab Markers, Recent Symptoms, Supplement Changes, Suggested Questions
- Footer: "Generated by HealthSignal on [date]"

---

## Implementation Order

```
1. Backend: User model + Alembic migration
2. Backend: auth routes (register, login), password hashing, JWT
3. Backend: get_current_user dependency wired into all protected routes
4. Backend: user_id enforcement in all repositories
5. AI agent: accept real user_id from request, propagate through supervisor
6. React: Login page + auth context + token attachment to all API calls
7. React: Logout, redirect-to-login on 401
8. AI agent: /query/stream endpoint with SSE
9. React: useChat updated to consume SSE stream, render tokens live
10. React: PDF export button on Report page (frontend library)
```

Steps 1–7 (auth + multi-user) must be done together — they are tightly coupled.
Steps 8–9 (streaming) are independent and can be done after auth.
Step 10 (PDF) is fully independent.

---

## What Does NOT Change

| | Before Phase 7 | After Phase 7 |
|---|---|---|
| Backend API structure | Same routes | Same routes + `/auth/*` + `/query/stream` |
| Data model | Same tables, `user_id` unenforced | Same tables, `user_id` enforced from JWT |
| AI agent logic | Same agents | Same agents, streaming added to query path |
| React UI | Single-user, no login | Login screen, per-user data, streaming chat |
| Doctor Report | Text only | Text + PDF download button |

All agent intelligence, memory, and data pipelines stay exactly the same.
