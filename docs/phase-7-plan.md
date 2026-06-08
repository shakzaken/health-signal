# Phase 7 — Auth, Multi-User, Streaming & PDF Export

## Overview

Phase 7 takes the product from a single-user personal tool to a proper multi-user application. It adds the four features that are required before this can be used by anyone other than the developer:

1. **Authentication** — secure login so only authorised users can access the app
2. **Multiple users** — each user sees only their own data, sessions, and history
3. **Streaming responses** — the AI answer appears word by word instead of after a long wait
4. **PDF export** — the doctor report can be downloaded as a PDF to bring to an appointment

---

## Feature 1 — Authentication

### Token strategy

| Decision | Choice |
|---|---|
| Token type | Single JWT access token (no refresh token) |
| Expiry | **24 hours** |
| Storage | **`localStorage`** — acceptable for a personal tool with a 1-day window |
| Attachment | `Authorization: Bearer <token>` header on every API call |
| On expiry | 401 → auto-redirect to login page, token cleared from localStorage |

### Registration flow (`POST /auth/register`)

1. User submits email + password
2. Backend checks email is not already taken (409 if duplicate)
3. Password hashed with **bcrypt** (one-way, salted — plain password never stored)
4. `User` row saved to DB
5. Returns a signed JWT — user is logged in immediately after registering

### Login flow (`POST /auth/login`)

1. User submits email + password
2. Backend looks up user by email (404 → 401 to avoid user enumeration)
3. bcrypt verifies submitted password against stored hash
4. On match → sign and return JWT: `{ sub: user_id, exp: now + 24h }`
5. React stores JWT in `localStorage`, redirects to the app

### Every subsequent request

```
Authorization: Bearer <token>
```

Backend and ai-agent validate the JWT signature and expiry on every protected request. No DB lookup needed — the user ID is encoded in the token.

### Password storage

- Library: `passlib[bcrypt]`
- bcrypt is slow by design (brute-force resistant) and automatically salted
- Two users with the same password always get different hashes

```
plain:  mysecretpassword
stored: $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
```

### Public routes (no JWT required)

- `POST /auth/register`
- `POST /auth/login`

All other routes on both the backend (`:8000`) and ai-agent (`:8001`) require a valid JWT.

### New backend pieces

- `models/user.py` — `User` table: `id (UUID)`, `email (TEXT UNIQUE)`, `hashed_password (TEXT)`, `created_at`
- `repositories/user_repository.py` — `get_by_email()`, `create()`
- `api/routes/auth.py` — `POST /auth/register`, `POST /auth/login`
- `core/security.py` — bcrypt hashing + JWT sign/verify (24h expiry, `python-jose`)
- `api/deps.py` — `get_current_user` dependency: validates JWT, returns user, raises 401 if invalid/expired
- Alembic migration for the `users` table

### New ai-agent pieces

- `core/security.py` — same JWT verify logic (shared secret, same algorithm)
- `api/deps.py` — `get_current_user` dependency wired into `/query` and `/query/stream`

### React changes

- `AuthContext` — holds the JWT and decoded `user_id` in React state, persists to `localStorage`
- Login page — email + password form, calls `POST /auth/login`, stores token on success
- Register page — same form with confirm password, calls `POST /auth/register`
- All `fetch` calls attach `Authorization: Bearer <token>` header
- On any 401 response → clear token, redirect to `/login`
- Logout button → clears localStorage token, redirects to `/login`

---

## Feature 2 — Multiple Users

### What changes

`user_id` is currently hardcoded to `"default"` everywhere. In Phase 7 it becomes the authenticated user's actual UUID from the JWT.

**Backend:**
- Every table already has a `user_id` column — it just needs to be populated from the JWT
- Every repository query already has a `user_id` filter — it just receives `"default"` now; it will receive the real ID
- The `get_current_user` dependency provides the real `user_id` to all routes automatically

**AI agent:**
- `user_id` flows from the JWT through the query request body
- The supervisor and all sub-agents already accept `user_id` — they just need to receive the real value
- Qdrant payloads already store `user_id` per chunk — retrieval is already filtered by it

**React:**
- `user_id` decoded from the JWT and attached to every API call body where needed
- No UI change — data isolation is invisible to the user

### Migration

Existing data under `user_id = "default"` stays as-is and can be reassigned manually if needed.

---

## Feature 3 — Streaming Responses

### What it does

Instead of waiting 5–10 seconds for the full AI answer to arrive, the response streams word by word into the chat window as the LLM generates it.

### AI agent side

- New endpoint: `POST /query/stream`
- FastAPI `StreamingResponse` with **Server-Sent Events (SSE)**
- LangChain `.astream()` instead of `.ainvoke()` — each token chunk sent as an SSE `data:` event
- Final SSE event carries the sources payload
- Existing `/query` (non-streaming) remains for non-chat use cases

### React side

- `useChat` reads the SSE stream via `fetch` + `ReadableStream`
- Each incoming chunk appended to the current assistant message in real time
- Blinking cursor shown while the stream is in progress
- Stream end event delivers sources, cursor removed

### What does NOT stream

- The Doctor Report — structured document, better displayed all at once
- The retrieval and agent reasoning steps — only the final answer generation streams

---

## Feature 4 — PDF Export

### What it does

A "Download as PDF" button on the Doctor Report page generates and downloads a formatted PDF — ready to print and bring to a doctor appointment.

### Approach — Frontend only (preferred)

- Library: `jsPDF` or `react-pdf` — generates PDF entirely in the browser
- No backend changes needed
- The report is structured plain text with clear section headers — easy to format client-side

### PDF contents

- Header: "Health Report — [date range]"
- Four sections: Abnormal Lab Markers, Recent Symptoms, Supplement Changes, Suggested Questions
- Footer: "Generated by HealthSignal on [date]"

---

## Implementation Order

```
── Auth + Multi-user (tightly coupled, done together) ──────────────
1.  Backend: Alembic migration — users table
2.  Backend: models/user.py, repositories/user_repository.py
3.  Backend: core/security.py — bcrypt + JWT (24h, python-jose)
4.  Backend: api/routes/auth.py — POST /auth/register, POST /auth/login
5.  Backend: api/deps.py — get_current_user dependency
6.  Backend: wire get_current_user into all existing protected routes
7.  Backend: replace hardcoded "default" user_id in all repositories
8.  AI agent: core/security.py + api/deps.py — same JWT verify
9.  AI agent: wire get_current_user into /query (and /query/stream later)
10. AI agent: propagate real user_id through supervisor and sub-agents
11. React: AuthContext + localStorage token management
12. React: Login page + Register page
13. React: attach Bearer token to all fetch calls
14. React: redirect to /login on 401, logout button

── Streaming (independent, after auth) ─────────────────────────────
15. AI agent: POST /query/stream — SSE streaming endpoint
16. React: useChat updated to consume SSE stream, render tokens live

── PDF Export (fully independent) ──────────────────────────────────
17. React: PDF export button on Report page (jsPDF or react-pdf)
```

---

## What Does NOT Change

| | Before Phase 7 | After Phase 7 |
|---|---|---|
| Backend API structure | Same routes | Same routes + `/auth/*` + `/query/stream` |
| Data model | Same tables, `user_id` unenforced | Same tables, `user_id` enforced from JWT |
| AI agent logic | Same agents | Same agents, streaming added to query path |
| React UI | Single-user, no login | Login + register screens, per-user data, streaming chat |
| Doctor Report | Text only | Text + PDF download button |

All agent intelligence, memory, and data pipelines stay exactly the same.
