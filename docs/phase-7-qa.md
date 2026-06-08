# Phase 7 QA — Auth, Multi-User, Streaming & PDF Export

## How to use this document

Work through each section top to bottom. Each test has:
- a **setup** (preconditions, curl commands, or UI steps)
- an **expected result** — what correct behaviour looks like
- a **❌ wrong if** — concrete signs the feature is broken

Run the services before starting:
```bash
# terminal 1 — backend
cd backend && uvicorn main:app --port 8000

# terminal 2 — ai-agent
cd ai-agent && uvicorn main:app --port 8001

# terminal 3 — frontend
cd frontend && npm run dev
```

---

## Feature 1 — Authentication

### 1.1 Registration — happy path

**Setup:**
```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "securepass123"}' | jq
```

**Expected:**
- HTTP 200
- Response body: `{ "access_token": "<jwt>", "token_type": "bearer" }`
- JWT is non-empty and has three dot-separated segments (header.payload.signature)

❌ Wrong if: 422, 500, or token is missing / `null`

---

### 1.2 Registration — duplicate email

**Setup:** Run the same register request from 1.1 a second time.

**Expected:**
- HTTP 409
- Error message indicates email already taken

❌ Wrong if: 500, or a second account is silently created

---

### 1.3 Registration — invalid email format

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "not-an-email", "password": "securepass123"}' | jq
```

**Expected:**
- HTTP 422
- Pydantic validation error on the `email` field

❌ Wrong if: 200 or the user is created with a malformed email

---

### 1.4 Login — happy path

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "securepass123"}' | jq
```

**Expected:**
- HTTP 200
- `{ "access_token": "<jwt>", "token_type": "bearer" }`
- Token is different from the registration token (new expiry)

❌ Wrong if: 401, 422, or same token returned every time (would mean expiry is static)

---

### 1.5 Login — wrong password

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "wrongpassword"}' | jq
```

**Expected:**
- HTTP 401
- Generic error message — must NOT say "password incorrect" (avoids confirming account exists)

❌ Wrong if: 200 with a token, or error message reveals which field was wrong

---

### 1.6 Login — unknown email

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nobody@example.com", "password": "anypassword"}' | jq
```

**Expected:**
- HTTP 401
- Same error message as 1.5 (must be indistinguishable — prevents user enumeration)

❌ Wrong if: 404 (reveals account does not exist)

---

### 1.7 Protected route — no token

```bash
curl -s http://localhost:8000/lab-results | jq
```

**Expected:**
- HTTP 401
- Body indicates authorisation is required

❌ Wrong if: 200 with data, or 403 (wrong status for missing credentials)

---

### 1.8 Protected route — tampered token

```bash
# Take a valid token and flip one character in the signature segment
curl -s http://localhost:8000/lab-results \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.TAMPERED.signature" | jq
```

**Expected:**
- HTTP 401
- Not a 500 (must not crash on bad token input)

❌ Wrong if: 200, 500, or any other status

---

### 1.9 Protected route — expired token

**Setup:** Temporarily set `ACCESS_TOKEN_EXPIRE_HOURS = 0` in `backend/core/security.py`, register a new user, restore the value, then use that token.

Alternatively, decode any valid JWT at [jwt.io](https://jwt.io), set `exp` to a past Unix timestamp, re-sign with the secret (if available in dev), and test.

**Expected:**
- HTTP 401
- Error indicates token is expired

❌ Wrong if: 200 with data (expired tokens must be rejected)

---

### 1.10 AI agent protected routes — no token

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "user_id": "anything"}' | jq
```

**Expected:**
- HTTP 401
- AI agent independently validates the JWT (does not trust the caller)

❌ Wrong if: 200, or ai-agent accepts the request without a token

---

### 1.11 AI agent — valid token accepted

```bash
TOKEN="<token from step 1.4>"
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "hello", "session_id": null}' | jq
```

**Expected:**
- HTTP 200 with an answer (even if no documents uploaded yet)
- AI agent does not return 401

❌ Wrong if: 401, or the token accepted by the backend is rejected by the ai-agent (different secret)

---

### 1.12 Frontend — login flow

1. Open `http://localhost:5173` while logged out
2. Verify you are redirected to `/login` (not the app)
3. Enter valid credentials → submit
4. Verify you land on the main app page
5. Open DevTools → Application → Local Storage → confirm `token` (or equivalent key) is present
6. Refresh the page — verify you stay logged in (token is restored from localStorage)

❌ Wrong if: app is accessible without logging in, or refresh resets to login

---

### 1.13 Frontend — logout

1. Log in
2. Click the logout button
3. Verify redirect to `/login`
4. Check Local Storage — token must be removed
5. Navigate back to `/` directly — verify redirect to `/login` again

❌ Wrong if: token remains in localStorage after logout, or app is still accessible

---

### 1.14 Frontend — 401 auto-redirect

1. Log in and load the app
2. In DevTools, delete the token from Local Storage (simulate expiry)
3. Ask a question in the chat
4. Verify the app detects the 401 and redirects to `/login` automatically

❌ Wrong if: app shows a blank error, crashes, or silently ignores the 401

---

## Feature 2 — Multi-User Data Isolation

> These tests require two separate registered accounts. Use Alice (from section 1) and register Bob.

```bash
# Register Bob
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "bobpass456"}' | jq
# Save Bob's token as BOB_TOKEN
```

---

### 2.1 Upload documents as Alice — then check Bob sees nothing

1. Log in as Alice, upload a blood test document via the UI (or API)
2. Log in as Bob (different browser / incognito)
3. Bob opens the app — document list must be empty

```bash
# Bob's perspective via API
curl -s http://localhost:8000/documents \
  -H "Authorization: Bearer $BOB_TOKEN" | jq
```

**Expected:** `[]` — Bob sees no documents

❌ Wrong if: Bob can see Alice's documents

---

### 2.2 Lab results are isolated

```bash
# Alice uploads a blood test → markers are parsed
# Check Bob sees no lab results
curl -s http://localhost:8000/lab-results \
  -H "Authorization: Bearer $BOB_TOKEN" | jq
```

**Expected:** `[]`

❌ Wrong if: Alice's lab results appear in Bob's response

---

### 2.3 Conversations are isolated

```bash
# Alice has chat history from prior tests
curl -s http://localhost:8000/conversations \
  -H "Authorization: Bearer $BOB_TOKEN" | jq
```

**Expected:** `[]` — Bob has no sessions

❌ Wrong if: Alice's sessions appear

---

### 2.4 Hardcoded `"default"` user_id is gone

```bash
# Search the codebase for any remaining hardcoded default user_ids
grep -rn '"default"' \
  /Users/yakir/projects/claude/health-signal/backend/api/routes/ \
  /Users/yakir/projects/claude/health-signal/ai-agent/api/routes/ \
  /Users/yakir/projects/claude/health-signal/frontend/src/
```

**Expected:** No matches (or only in comments / test fixtures)

❌ Wrong if: route handlers still pass `"default"` as a user_id

---

### 2.5 Qdrant isolation — AI agent uses real user_id for retrieval

1. As Alice, upload a document and ask "What are my lab results?"
2. As Bob (no documents), ask the same question
3. Bob's answer should say no relevant documents were found — it must NOT cite Alice's data

❌ Wrong if: Bob's answer references Alice's health data

---

### 2.6 user_id in JWT matches what reaches the database

```bash
# Decode Alice's JWT (base64 decode the middle segment)
echo "<alice_token_payload_segment>" | base64 -d 2>/dev/null | python3 -m json.tool
# Note the "sub" field — this should be Alice's UUID

# Check that Alice's documents are stored under that UUID
curl -s http://localhost:8000/documents \
  -H "Authorization: Bearer $ALICE_TOKEN" | jq '.[0].user_id'
```

**Expected:** `user_id` in the DB record matches `sub` in the JWT

❌ Wrong if: `user_id` is `"default"` or a different value

---

## Feature 3 — Streaming Responses

### 3.1 SSE endpoint exists and returns the right Content-Type

```bash
TOKEN="<alice token>"
curl -s -N -X POST http://localhost:8001/query/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question": "What are my lab results?", "session_id": null}' &
sleep 3 && kill %1
```

**Expected:**
- Response `Content-Type` is `text/event-stream`
- Output starts within ~1 second (not after the full answer is generated)
- Each line looks like `data: {"token": "some text"}`
- Final event carries sources: `data: {"sources": [...]}`

❌ Wrong if: Content-Type is `application/json`, nothing is received for >5 seconds, or the whole answer arrives at once

---

### 3.2 Tokens arrive incrementally (timing check)

1. In the browser, open the chat and ask a question that produces a long answer (e.g. "Give me a full summary of my health history")
2. Open DevTools → Network → filter by `stream` or `query`
3. Watch the response tab — text should grow word by word

**Expected:**
- First words appear within ~1 second
- The message visibly builds up in the UI character by character or word by word
- Blinking cursor is visible while generation is in progress
- Cursor disappears when the stream ends

❌ Wrong if: UI stays blank for 5+ seconds then the full answer appears at once

---

### 3.3 Sources appear at the end of the stream

After the stream completes (cursor disappears), the source panel should populate with the document chunks that were used.

**Expected:**
- Source panel is empty while streaming
- Sources appear after the stream ends (not before, not missing entirely)

❌ Wrong if: sources never appear, or source panel shows mid-stream

---

### 3.4 Doctor Report does NOT stream

1. Go to the Report page and generate a Doctor Report
2. Verify the report appears all at once (loading spinner → full text)
3. Check Network tab — request goes to `/report` or `/query` (non-stream endpoint), not `/query/stream`

❌ Wrong if: the Doctor Report uses SSE or partially renders while generating

---

### 3.5 Non-streaming `/query` endpoint still works

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my hemoglobin?", "session_id": null}' | jq
```

**Expected:**
- HTTP 200 with `{ "answer": "...", "sources": [...] }`
- Response is the full answer (not SSE format)

❌ Wrong if: 404, or the response is in SSE format

---

### 3.6 Stream aborted mid-way — no server error

1. Start a streaming chat request in the browser
2. While words are appearing, navigate away from the page (or close the tab)
3. Check the backend/ai-agent logs

**Expected:**
- No unhandled exceptions or 500 errors in the logs
- The server cleans up gracefully (no stuck coroutines)

❌ Wrong if: server logs show errors or the process hangs

---

### 3.7 Auth applies to `/query/stream`

```bash
curl -s -N -X POST http://localhost:8001/query/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "session_id": null}'
```

**Expected:** HTTP 401, no stream begins

❌ Wrong if: stream starts without a token

---

## Feature 4 — PDF Export

### 4.1 Download button is present on the Report page

1. Log in as Alice (with documents uploaded)
2. Navigate to the Report/Doctor Report page
3. Generate a report

**Expected:**
- A "Download as PDF" (or equivalent) button is visible after the report loads
- Button is NOT visible before the report has loaded

❌ Wrong if: button is missing, or visible before any report is generated

---

### 4.2 PDF downloads successfully

1. Click the Download button
2. Verify a `.pdf` file is downloaded (check the browser downloads folder)
3. Open the PDF

**Expected:**
- File opens in a PDF viewer without errors
- File is not empty and not corrupt

❌ Wrong if: download fails, file is 0 bytes, or the file is corrupt

---

### 4.3 PDF contents are correct

Open the downloaded PDF and verify:

| Section | Expected |
|---|---|
| Header | "Health Report" with a date range |
| Section 1 | Abnormal Lab Markers |
| Section 2 | Recent Symptoms |
| Section 3 | Supplement Changes |
| Section 4 | Suggested Questions for Doctor |
| Footer | "Generated by HealthSignal on [date]" |

❌ Wrong if: sections are missing, header has no date, or footer is absent

---

### 4.4 PDF is generated client-side (no backend call)

1. Open DevTools → Network
2. Click the Download button
3. Inspect all outgoing requests

**Expected:**
- No new HTTP request is made to `localhost:8000` or `localhost:8001` when clicking Download
- PDF generation is entirely in the browser (jsPDF / react-pdf)

❌ Wrong if: a backend API call is made to generate the PDF

---

### 4.5 PDF filename is sensible

**Expected:**
- Downloaded filename includes the date or something identifiable, e.g. `health-report-2026-06-08.pdf`
- Not a generic browser-assigned name like `download.pdf` or `query`

❌ Wrong if: filename is blank or a random UUID

---

## Cross-cutting security checks

### S.1 No plain-text password in database

```bash
# Connect to Postgres and inspect the users table
psql -U postgres -d healthsignal -c "SELECT email, hashed_password FROM users LIMIT 5;"
```

**Expected:**
- `hashed_password` starts with `$2b$` (bcrypt format)
- The plain password is NOT visible anywhere

❌ Wrong if: plain password is stored, or hash doesn't look like bcrypt

---

### S.2 JWT secret is not hardcoded in source

```bash
grep -rn "secret_key\s*=\s*['\"]" \
  /Users/yakir/projects/claude/health-signal/backend/ \
  /Users/yakir/projects/claude/health-signal/ai-agent/ \
  --include="*.py" | grep -v ".venv"
```

**Expected:** No hardcoded string value — secret must come from an environment variable / `.env` file

❌ Wrong if: a literal string like `"mysecret"` or `"changeme"` appears as the value

---

### S.3 Backend and AI agent share the same JWT secret

1. Register a user on the backend (get a token)
2. Send that same token to the AI agent's `/query` endpoint
3. Verify the AI agent accepts it (step 1.11 above covers this explicitly)

If the AI agent uses a different secret, it will return 401 even with a valid backend-issued token.

---

### S.4 All existing protected backend routes require auth

For each route below, send a request **without** an Authorization header and verify HTTP 401:

```bash
for ROUTE in \
  "GET /lab-results" \
  "GET /documents" \
  "GET /symptom-entries" \
  "GET /supplement-entries" \
  "GET /timeline" \
  "GET /conversations"
do
  METHOD=$(echo $ROUTE | cut -d' ' -f1)
  PATH=$(echo $ROUTE | cut -d' ' -f2)
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X $METHOD http://localhost:8000$PATH)
  echo "$ROUTE → $STATUS"
done
```

**Expected:** Every route returns `401`

❌ Wrong if: any returns `200` or `403`

---

## Regression — existing functionality must still work

After Phase 7, all Phase 3–6 features must continue to work for an authenticated user. Run a quick smoke test:

| Test | How to verify |
|---|---|
| Upload a document | Upload via UI as Alice → check it appears in the document list |
| Lab parsing | Upload a blood test → `GET /lab-results` returns parsed markers |
| Ask a lab question | "What is my Vitamin D?" → routes to `lab_analysis`, returns a value |
| Pattern detection | "Did my fatigue improve after supplements?" → routes to `pattern_detection` |
| Timeline | "What happened in 2025?" → chronological narrative returned |
| RAG | "What did my doctor say about diet?" → returns document quotes |
| Doctor report | Report page generates a full structured report |
| Conversation memory | Ask a follow-up question in the same session → agent uses prior context |

❌ Wrong if: any of the above breaks after auth is wired in
